import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from ApiEngine.core import TestRunner

from service.core.enums import CaseRunStatus, CaseRunType
from service.test_environment.variable.global_config_service import ProjectGlobalConfigService
from service.test_execution.models import ApiCaseRunRecord

logger = logging.getLogger(__name__)


def _make_json_safe(obj: Any) -> Any:
    """Recursively convert non-JSON-serializable types for orjson.

    Handles CaseInsensitiveDict (requests headers), bytes, and other
    common non-serializable types returned by the ApiEngine.
    """
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_json_safe(v) for v in obj]
    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8", errors="replace")
        except Exception:
            return obj.hex()
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if hasattr(obj, "items"):
        # MutableMapping subclasses (e.g. CaseInsensitiveDict)
        return {str(k): _make_json_safe(v) for k, v in obj.items()}
    return str(obj)


def _build_request_info(result: dict, case_payload: dict) -> dict:
    """Build request_info from engine result, using the actual URL with replaced params."""
    from urllib.parse import urlparse, parse_qs
    actual_url = result.get('url') or ''
    method = result.get('method') or case_payload.get('method', '')
    # Parse actual query params from the URL the engine sent (has replaced values)
    params = {}
    if actual_url:
        try:
            parsed = urlparse(actual_url)
            for k, v in parse_qs(parsed.query).items():
                params[k] = v[0] if len(v) == 1 else v
        except Exception:
            pass
    if not params:
        params = case_payload.get('request', {}).get('params') or {}
    return {
        'method': method.upper(),
        'url': actual_url,
        'headers': result.get('request_headers') or {},
        'params': params,
        'body': result.get('request_body') or case_payload.get('request', {}).get('data') or case_payload.get('request', {}).get('json'),
    }


def map_runner_status(result: dict[str, Any]) -> CaseRunStatus:
    status = (result.get("status") or "").lower()
    if status == "success":
        return CaseRunStatus.success
    if status == "fail":
        return CaseRunStatus.fail
    return CaseRunStatus.error


class RunnerGateway:
    @classmethod
    async def execute_case_payload(
        cls,
        *,
        test_env_data: dict[str, Any],
        case_payload: dict[str, Any],
        case_name: str,
        api_case_id: int | None = None,
        interface_id: int | None = None,
        suite_run_id: int | None = None,
        task_run_id: int | None = None,
        environment_id: int | None = None,
        env_snapshot_id: int | None = None,
        triggered_by_id: int | None = None,
        run_type: CaseRunType = CaseRunType.suite,
        project_id: int | None = None,
        run_id: str | None = None,
        writeback_global: bool = True,
        existing_record_id: int | None = None,
    ) -> ApiCaseRunRecord:
        # 构建 runner 环境（浅copy，引擎内部会再做 deepcopy）
        runner_env = dict(test_env_data)
        runner = TestRunner(runner_env, run_id=run_id)
        start = datetime.now(timezone.utc)
        
        # 初始化详细结果信息
        detailed_result = {
            'status': 'pending',
            'executor': triggered_by_id or None,
            'duration_ms': 0,
            'error_message': None,
            'log_data': [],
        }
        
        try:
            result = await asyncio.to_thread(runner.execute_cases, case_payload)

            # 解析引擎返回的详细结果
            if isinstance(result, dict):
                detailed_result['status'] = result.get('status', 'unknown')
                detailed_result['error_message'] = result.get('message') if result.get('status') == 'error' else None

                # 引擎单条用例结果使用 flat 结构：response_code, response_headers, response_body,
                # request_headers, request_body, url, method, log_data
                # 也可能有嵌套的 response_info / request_info（兼容两种格式）
                ri = result.get('response_info') or {}
                detailed_result.update({
                    'response_info': {
                        'status_code': ri.get('status_code') or result.get('response_code'),
                        'content_type': ri.get('content_type') or result.get('content_type'),
                        'body': ri.get('body') or result.get('response_body'),
                        'elapsed_ms': ri.get('elapsed_ms') or result.get('run_time'),
                        'headers': ri.get('headers') or result.get('response_headers') or {},
                    },
                    'request_info': _build_request_info(result, case_payload),
                    'extract_info': result.get('extract_info') or result.get('extracts') or [],
                    'assert_info': result.get('assert_info') or result.get('assertions') or [],
                    'log_data': result.get('log_data') or result.get('logs') or [],
                })
                
                # 如果断言信息没有passed字段，尝试从结果中推断
                assertions = detailed_result.get('assert_info', [])
                for assertion in assertions:
                    if 'passed' not in assertion:
                        # 默认认为断言通过（除非明确标记为失败）
                        assertion['passed'] = assertion.get('success', True)
            
            # 将详细结果合并到result中，供api_requests_info存储
            result['_debug_detail'] = detailed_result
            
        except Exception as exc:
            result = {"status": "error", "message": str(exc)}
            detailed_result['status'] = 'error'
            detailed_result['error_message'] = str(exc)
            detailed_result['log_data'].append(['ERROR', f'执行异常: {str(exc)}'])
            result['_debug_detail'] = detailed_result
            
        end = datetime.now(timezone.utc)
        
        # 计算耗时（毫秒）
        duration_ms = int((end - start).total_seconds() * 1000)
        detailed_result['duration_ms'] = duration_ms
        if '_debug_detail' in result:
            result['_debug_detail']['duration_ms'] = duration_ms

        # ---- 全局变量写DB ----
        if writeback_global and project_id is not None:
            if run_id:
                # 套件模式：从 _suite_stores 提取 debug_updates
                debug_updates = TestRunner.get_debug_updates(run_id)
                if debug_updates:
                    await ProjectGlobalConfigService.apply_engine_writeback(
                        project_id, debug_updates
                    )
                    TestRunner.clear_debug_updates(run_id)
            else:
                # 退化模式（单用例调试）：从引擎快照提取
                engine_snapshot = runner.get_env_snapshot()
                debug_updates = engine_snapshot.get("debug_updates") or {}
                if debug_updates:
                    await ProjectGlobalConfigService.apply_engine_writeback(
                        project_id, debug_updates
                    )

        status = map_runner_status(result if isinstance(result, dict) else {})
        safe_result = _make_json_safe(result) if isinstance(result, dict) else None
        if existing_record_id:
            # 更新已有记录（异步调试模式）
            record = await ApiCaseRunRecord.get(id=existing_record_id)
            record.status = status
            record.case_snapshot = case_payload
            record.error_message = result.get("message") if isinstance(result, dict) else None
            record.start_time = start
            record.end_time = end
            record.duration_ms = int((end - start).total_seconds() * 1000)
            record.api_requests_info = safe_result
            await record.save()
            return record
        else:
            return await ApiCaseRunRecord.create(
                api_case_id=api_case_id,
                interface_id=interface_id,
                suite_run_id=suite_run_id,
                task_run_id=task_run_id,
                run_type=run_type,
                environment_id=environment_id,
                env_snapshot_id=env_snapshot_id,
                triggered_by_id=triggered_by_id,
                case_name=case_name,
                status=status,
                case_snapshot=case_payload,
                error_message=result.get("message") if isinstance(result, dict) else None,
                start_time=start,
                end_time=end,
                duration_ms=int((end - start).total_seconds() * 1000),
                api_requests_info=safe_result,
            )

    @classmethod
    async def run_interface_debug(
        cls,
        *,
        interface,
        environment_id: int,
        payload: dict[str, Any] | None,
        triggered_by_id: int,
    ) -> ApiCaseRunRecord:
        from service.api_test.shared.payload_builder import build_runner_case_from_payload
        from service.test_environment.variable.assembler import TestEnvDataAssembler

        test_env_data = await TestEnvDataAssembler.get_test_env_data(environment_id)
        runner_case = build_runner_case_from_payload(interface, payload)
        record = await cls.execute_case_payload(
            test_env_data=test_env_data,
            case_payload=runner_case,
            case_name=runner_case.get("title") or interface.path,
            interface_id=interface.id,
            environment_id=environment_id,
            triggered_by_id=triggered_by_id,
            run_type=CaseRunType.debug,
            project_id=interface.project_id,
        )
        interface.last_debug_environment_id = environment_id
        await interface.save(update_fields=["last_debug_environment_id", "updated_at"])
        return record

    @classmethod
    async def run_case_debug(
        cls,
        *,
        case_id: int,
        environment_id: int,
        triggered_by_id: int,
        existing_record_id: int | None = None,
    ) -> ApiCaseRunRecord:
        from service.api_test.models import ApiTestCase
        from service.test_environment.models import TestEnvironment
        from service.test_environment.variable.assembler import TestEnvDataAssembler
        from service.test_execution.case_prepare_service import prepare_case_payload

        case = await ApiTestCase.get(id=case_id)
        env = await TestEnvironment.get_or_none(id=environment_id)
        test_env_data = await TestEnvDataAssembler.get_test_env_data(environment_id)
        project_id = env.project_id if env else None

        # ---- 按 precondition_ids 加载关联的前置用例 ----
        pre_ids = (case.case_payload or {}).get("precondition_ids") or []
        pre_cases = []
        if pre_ids:
            pre_cases = await ApiTestCase.filter(id__in=pre_ids).order_by("sort_order", "id")
        logger.info(
            "[debug] run_case_debug: case_id=%s, precondition_ids=%s, 加载 %d 个前置用例",
            case.id, pre_ids, len(pre_cases),
        )

        # ---- 构建主用例 payload，嵌入前置用例（合并为一次引擎调用） ----
        prepared_main = await prepare_case_payload(project_id, case.case_payload)
        if pre_cases:
            from service.api_test.shared.payload_builder import _normalize_template_vars, _normalize_in_structure
            engine_preconditions = []
            for pc in pre_cases:
                prepared_pc = await prepare_case_payload(project_id, pc.case_payload)
                # 防御性归一化：确保 DB 中的 {var} 格式被转换为引擎识别的 ${var}
                iface = prepared_pc.get("interface") or {}
                if iface.get("url"):
                    iface["url"] = _normalize_template_vars(iface["url"])
                if prepared_pc.get("path"):
                    prepared_pc["path"] = _normalize_template_vars(prepared_pc["path"])
                req = prepared_pc.get("request") or {}
                if req:
                    prepared_pc["request"] = _normalize_in_structure(req)
                engine_preconditions.append(prepared_pc)
            prepared_main["preconditions"] = engine_preconditions

        # ---- 一次引擎调用：前置 + 主用例在同一 Session 中执行 ----
        record = await cls.execute_case_payload(
            test_env_data=test_env_data,
            case_payload=prepared_main,
            case_name=case.title,
            api_case_id=case.id,
            interface_id=case.interface_id,
            environment_id=environment_id,
            triggered_by_id=triggered_by_id,
            run_type=CaseRunType.debug,
            project_id=project_id,
            existing_record_id=existing_record_id,
        )

        # ---- 从前置步骤独立结果更新各 DB 前置用例 ----
        if pre_cases:
            await cls._update_precondition_results(pre_cases, record)

        # ---- 更新主用例状态 ----
        case.last_run_at = record.end_time
        case.exec_status = record.status.value
        case.updated_by_id = triggered_by_id
        await case.save(update_fields=["last_run_at", "exec_status", "updated_by_id", "updated_at"])
        return record

    @classmethod
    async def _update_precondition_results(
        cls,
        pre_cases: list,
        main_record: "ApiCaseRunRecord",
    ) -> None:
        """从主用例执行结果中解析前置步骤数据，更新各 DB 前置用例。

        引擎 (BaseCase) 为每个前置步骤记录独立的执行结果
        （precondition_results），包含完整的响应/请求/断言数据。
        """
        from service.core.enums import ExecStatus

        log_data: list = []
        pre_step_data: dict[str, dict] = {}  # title → per-step engine result

        if isinstance(main_record.api_requests_info, dict):
            dd = main_record.api_requests_info.get("_debug_detail") or {}
            log_data = dd.get("log_data") or []
            # 收集 per-step 前置结果
            for ps in (main_record.api_requests_info.get("precondition_results") or []):
                t = (ps.get("title") or "").strip()
                if t:
                    pre_step_data[t] = ps

        # 构建 title 映射（精确 + 模糊匹配）
        engine_titles = list(pre_step_data.keys())
        db_titles = [pc.title for pc in pre_cases]
        logger.info(
            "[debug] _update_precondition_results: engine titles=%s, db titles=%s",
            engine_titles, db_titles,
        )

        def _find_step(db_title: str) -> dict:
            """精确匹配 → 包含匹配 → 索引匹配"""
            if db_title in pre_step_data:
                return pre_step_data[db_title]
            # 模糊匹配：引擎标题包含 DB 标题，或反之
            for et, step in pre_step_data.items():
                if db_title in et or et in db_title:
                    logger.info("[debug] 模糊匹配: '%s' → '%s'", db_title, et)
                    return step
            return {}

        # 按 title 收集日志和状态
        pre_logs: dict[str, list] = {}
        pre_status: dict[str, str] = {}
        current_title = None

        for entry in log_data:
            if not isinstance(entry, (list, tuple)) or len(entry) < 2:
                continue
            level = str(entry[0])
            msg = " ".join(str(x) for x in entry[1:])

            if "执行前置步骤:" in msg:
                current_title = msg.split("执行前置步骤:")[-1].strip()
                pre_logs.setdefault(current_title, [])
            elif current_title:
                pre_logs.setdefault(current_title, []).append([level, msg])

            if "前置完成:" in msg:
                title = msg.split("前置完成:")[-1].strip()
                pre_status.setdefault(title, "success")
            elif "前置失败:" in msg or "前置执行异常:" in msg:
                parts = msg.split(":")
                if len(parts) >= 2:
                    title = parts[-1].strip().split("—")[0].strip()
                    pre_status[title] = "fail"

        # 更新各 DB 前置用例
        for pc in pre_cases:
            status = pre_status.get(pc.title)
            logs = pre_logs.get(pc.title, [])
            step = _find_step(pc.title)

            # 从 per-step 数据推断状态 — HTTP status_code 始终优先
            sc = step.get("status_code", "")
            if sc and not str(sc).startswith("2"):
                # HTTP 非 2xx 一律视为失败，不管引擎 status 怎么说
                status = "fail"
            elif status is None and step:
                # 检查 assert_info 是否有失败的断言
                assert_info = step.get("assert_info") or []
                has_failed_assert = any(
                    a.get("passed") is False for a in assert_info
                )
                if has_failed_assert:
                    status = "fail"
                else:
                    # 引擎 status + 2xx status_code → success
                    status = step.get("status") or "success"
            elif status is None:
                status = "success" if main_record.status == CaseRunStatus.success else "fail"

            payload_copy = dict(pc.case_payload)

            pc.exec_status = (
                ExecStatus.success if status == "success" else ExecStatus.fail
            )
            payload_copy["_exec_result"] = {
                "status": status,
                "response_code": step.get("status_code", ""),
                "response_body": step.get("response_body"),
                "response_headers": step.get("response_headers", {}),
                "request_headers": step.get("request_headers") or payload_copy.get("headers") or {},
                "request_body": step.get("request_body"),
                "method": step.get("method", ""),
                "url": step.get("url", ""),
                "run_time": step.get("run_time", 0),
                "log_data": logs,
                "assert_info": step.get("assert_info") or [],
                "extract_info": step.get("extract_info") or [],
            }
            pc.case_payload = payload_copy
            await pc.save(
                update_fields=["exec_status", "case_payload", "updated_at"],
            )

            # 为前置用例创建独立的执行记录
            run_status = CaseRunStatus.success if status == "success" else CaseRunStatus.fail
            # run_time 可能是数字（秒）或字符串（如 "46 ms"），需要安全解析
            step_duration_ms = 0
            raw_rt = step.get("run_time")
            if raw_rt is not None:
                if isinstance(raw_rt, (int, float)):
                    step_duration_ms = int(raw_rt * 1000) if raw_rt < 1000 else int(raw_rt)
                elif isinstance(raw_rt, str):
                    import re
                    nums = re.findall(r'[\d.]+', raw_rt)
                    if nums:
                        try:
                            val = float(nums[0])
                            step_duration_ms = int(val) if 'ms' in raw_rt.lower() else int(val * 1000)
                        except (ValueError, OverflowError):
                            pass
            if not step_duration_ms and main_record.duration_ms:
                step_duration_ms = main_record.duration_ms
            try:
                pre_record = await ApiCaseRunRecord.create(
                    api_case_id=pc.id,
                    interface_id=pc.interface_id,
                    run_type=CaseRunType.debug,
                    environment_id=main_record.environment_id,
                    triggered_by_id=main_record.triggered_by_id,
                    case_name=pc.title,
                    status=run_status,
                    start_time=main_record.start_time,
                    end_time=main_record.end_time,
                    duration_ms=step_duration_ms,
                    api_requests_info={
                        "_precondition_detail": step,
                        "log_data": logs,
                    },
                )
                logger.info("[debug] Created run record for precondition case %s (record_id=%s, status=%s, duration_ms=%s)", pc.id, pre_record.id, run_status, step_duration_ms)
            except Exception as e:
                logger.warning("Failed to create run record for precondition case %s: %s", pc.id, e)
