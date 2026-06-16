"""
  1、根据接口文档生成基础的接口用例
  2、根据基础的接口用例，生成可执行的结构化接口用例
  3、保存结构化接口用例到数据库
"""
import io
import json
import operator
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Annotated, Any, List, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer
from langgraph.constants import END, START
from langgraph.graph import StateGraph

from config.settings import BASE_DIR, MAX_BATCH_SIZE
from service.ai_generation.common import build_default_additional_info
from service.core.enums import ReviewStatus
from utils.logger.logger import _ThreadSafeStdout
from workflow.api_basecase_workflow import ApiBaseCaseGeneratorWorkflow, StateNode
from workflow.api_runcase_workflow import APIRuncaseGeneratorWorkflow, APIState

checkpointer = InMemorySaver()


@dataclass
class BaseCasePreRunResult:
    """单条基础用例经 APIRuncaseGeneratorWorkflow 预执行后的结果。"""

    index: int
    api_case: dict
    review_status: ReviewStatus
    error: str | None = None


def _normalize_pre_run_output(result: dict, base_case: dict) -> tuple[dict, ReviewStatus]:
    review_raw = result.get("review_status") or ReviewStatus.init.value
    try:
        review = ReviewStatus(review_raw)
    except ValueError:
        review = ReviewStatus.error

    api_case = result.get("api_case") or {}
    if isinstance(api_case, list) and api_case:
        api_case = api_case[0]
    if not isinstance(api_case, dict):
        api_case = {"title": base_case.get("name"), "steps": base_case.get("steps")}
    return api_case, review


def concurrent_pre_run_base_cases(
    base_cases: list[dict],
    *,
    api_doc: str,
    indices: list[int] | None = None,
    precoditions_api_doc: list | None = None,
    environment_id: int = 0,
    project_id: int | str | None = None,
    test_env_data: dict | None = None,
    additional_info: dict | None = None,
    generator_count: int = 0,
    config: dict[str, Any] | RunnableConfig | None = None,
    max_workers: int | None = None,
    progress_callback=None,
) -> list[BaseCasePreRunResult]:
    """ThreadPoolExecutor 并发预执行基础用例（共享入口，供主工作流与 api_test confirm 复用）。

    progress_callback: 可选回调，签名 callback(completed: int, total: int, item: dict)
        item 包含 {index, name, status, error}，每完成一个用例调用一次。
    """
    if not base_cases:
        return []

    if indices is None:
        indices = list(range(len(base_cases)))
    if len(indices) != len(base_cases):
        raise ValueError("indices 长度须与 base_cases 一致")

    run_config = config or {"configurable": {"thread_id": "api-runcase-concurrent"}}
    workers = max_workers or MAX_BATCH_SIZE

    _safe_stdout = _ThreadSafeStdout(sys.stdout)
    sys.stdout = _safe_stdout
    task_outputs: dict[Any, tuple[io.StringIO, int, dict]] = {}

    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_list = []
            for batch_idx, (orig_idx, base_case) in enumerate(zip(indices, base_cases)):
                workflow = APIRuncaseGeneratorWorkflow().create_runcase_workflow()
                buf = io.StringIO()
                invoke_input: dict[str, Any] = {
                    "base_case": base_case,
                    "api_doc": api_doc,
                    "environment_id": environment_id,
                    "generator_count": generator_count,
                }
                if precoditions_api_doc is not None:
                    invoke_input["precoditions_api_doc"] = precoditions_api_doc
                if project_id is not None:
                    invoke_input["project"] = str(project_id)
                if test_env_data is not None:
                    invoke_input["test_env_data"] = test_env_data
                if additional_info is not None:
                    invoke_input["additional_info"] = additional_info

                invoke_kwargs = {"input": invoke_input, "config": run_config}

                def _run_with_buffer(wf, kwargs, buffer, _batch_idx=batch_idx):
                    _safe_stdout.set_buffer(buffer)
                    return wf.invoke(**kwargs)

                future = executor.submit(
                    _run_with_buffer, workflow, invoke_kwargs, buf
                )
                task_outputs[future] = (buf, orig_idx, base_case)
                future_list.append(future)

            results: list[BaseCasePreRunResult] = []
            total = len(future_list)
            for pos, future in enumerate(future_list, start=1):
                buf, orig_idx, base_case = task_outputs[future]
                try:
                    raw = future.result()
                    api_case, review = _normalize_pre_run_output(raw, base_case)
                    results.append(
                        BaseCasePreRunResult(
                            index=orig_idx,
                            api_case=api_case,
                            review_status=review,
                        )
                    )
                    if progress_callback:
                        progress_callback(pos, total, {
                            "index": orig_idx,
                            "name": base_case.get("name", ""),
                            "status": "success" if review == ReviewStatus.success else "warning",
                            "error": None,
                        })
                except Exception as exc:
                    results.append(
                        BaseCasePreRunResult(
                            index=orig_idx,
                            api_case={
                                "title": base_case.get("name"),
                                "steps": base_case.get("steps"),
                            },
                            review_status=ReviewStatus.error,
                            error=str(exc),
                        )
                    )
                    if progress_callback:
                        progress_callback(pos, total, {
                            "index": orig_idx,
                            "name": base_case.get("name", ""),
                            "status": "error",
                            "error": str(exc),
                        })

                task_log = buf.getvalue()
                if task_log.strip():
                    print(
                        f"\n{'=' * 20} 预执行任务 {pos}/{len(future_list)} 输出 {'=' * 20}"
                    )
                    print(task_log, end="")
    finally:
        sys.stdout = _safe_stdout._original

    return results


class mainState(TypedDict):
    api_doc: str  # API接口文档
    environment_id: int  # 测试环境 ID，>0 时从平台加载 test_env_data
    precoditions: list[str]  # 前置执行依赖接口的调用顺序
    base_cases: List  # 生成的测试用例（所有用例 - 列表）
    base_case: dict # 生成的基础测试用例（单个用例 - 预执行）
    test_env_data: dict # 全局环境数据（含可定义函数、测试数据、数据库环境配置等）
    additional_info: dict # 额外信息（含项目名称、模块名称、注意事项等）
    generator_count:int  # 重新生成结构化测试用例的次数
    api_run_cases: Annotated[List,operator.add]  # 最终生成的可运行用例

# 主工作流(使用多线程并发 生成可执行的接口测试用例)
class APICaseGeneratorMainWorkflow:
    """
    1、根据接口文档生成基础的接口用例
    2、根据基础的接口用例，生成可执行结构化接口用例
    3、保存结构化接口用例到数据库
    """
    # 1、根据接口文档生成基础的接口用例
    def generator_api_basecase(self,state:mainState,config: RunnableConfig):
        writer = get_stream_writer()
        writer("【开始执行主流程节点】 1、生成api基础测试用例：")
        workflow = ApiBaseCaseGeneratorWorkflow().create_basecase_workflow()
        basecase_state:StateNode = workflow.invoke(
                                    {"api_doc": state.get("api_doc"), "precoditions": state.get("precoditions")},
                                   config=config
                                   )
        writer("【执行主流程节点完成】 1、生成api基础测试用例：")
        return {"base_cases":basecase_state.get("api_cases")}

    # 2、根据基础的接口用例，生成可执行结构化接口用例
    def generator_api_structure_runcase(self, state: mainState, config: RunnableConfig):
        """并发预执行：复用 concurrent_pre_run_base_cases。"""
        writer = get_stream_writer()
        writer("【开始执行主流程节点】 2、生成可执行结构化接口用例：")
        results = concurrent_pre_run_base_cases(
            state.get("base_cases") or [],
            api_doc=state.get("api_doc") or "",
            environment_id=state.get("environment_id") or 0,
            test_env_data=state.get("test_env_data"),
            additional_info=state.get("additional_info"),
            generator_count=state.get("generator_count") or 0,
            config=config,
        )
        writer("【执行主流程节点完成】 2、生成可执行结构化接口用例")
        return {"api_run_cases": [r.api_case for r in results]}

    # 3、保存结构化接口用例到数据库
    def save_api_runcase_to_db(self,state:mainState):
        writer = get_stream_writer()
        writer("【开始执行主流程节点】 4、保存结构化接口用例到数据库：")
        # 保存结构化接口用例到数据库
        # 将结构化接口用例写入到文件 test_data下的api_run_cases.json 中
        file_path = BASE_DIR + "/test_data/api_run_cases.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state.get("api_run_cases"), f, ensure_ascii=False, indent=4)
        writer(f"一共生成 {len(state.get('api_run_cases'))} 个结构化接口用例，并保存到 {file_path} 中")
        writer("【执行主流程节点完成】 4、保存结构化接口用例到数据库：")
        return {}

    # 6、创建主工作流
    def create_main_workflow(self):
        # 1、添加节点
        builder = StateGraph(mainState)
        builder.add_node("generator_api_basecase",self.generator_api_basecase)
        builder.add_node("generator_api_structure_runcase",self.generator_api_structure_runcase)
        builder.add_node("save_api_runcase_to_db",self.save_api_runcase_to_db)
        # 2、对执行节点进行编排
        builder.add_edge(START, "generator_api_basecase")
        builder.add_edge("generator_api_basecase", "generator_api_structure_runcase")
        builder.add_edge("generator_api_structure_runcase", "save_api_runcase_to_db")
        builder.add_edge("save_api_runcase_to_db", END)
        # 3、返回工作流
        return builder.compile(checkpointer=checkpointer)


if __name__ == '__main__':
    import sys

    from service.core import config as core_config

    if not core_config.AITESTPLATFORM_ALLOW_WORKFLOW_MAIN:
        print("Set AITESTPLATFORM_ALLOW_WORKFLOW_MAIN=1 to run this workflow demo")
        sys.exit(0)
    api_doc = """[
        {
            "path": "/member/public/login",
            "method": "POST",
            "summary": "登录",
            "parameters": {
                "header": [
                    {
                        "name": "Content-Type",
                        "type": "string",
                        "description": "",
                        "required": true
                    }
                ],
                "path": [],
                "query": []
            },
            "requestBody": {
                "content_type": "application/x-www-form-urlencoded",
                "body": [
                    {
                        "name": "keywords",
                        "type": "string",
                        "description": "手机号",
                        "required": true
                    },
                    {
                        "name": "password",
                        "type": "string",
                        "description": "密码",
                        "required": true
                    }
                ]
            },
            "responses": [
                {
                    "http_code": "200",
                    "description": "登录成功",
                    "media_type": "application/json",
                    "response_body": {
                        "status": 200,
                        "description": "登录成功"
                    }
                },
                {
                    "http_code": "200",
                    "description": "用户不存在",
                    "media_type": "application/json",
                    "response_body": {
                        "status": 100,
                        "description": "用户不存在"
                    }
                },
                {
                    "http_code": "200",
                    "description": "密码不能为空",
                    "media_type": "application/json",
                    "response_body": {
                        "status": 100,
                        "description": "密码不能为空"
                    }
                },
                {
                    "http_code": "200",
                    "description": "密码错误1次",
                    "media_type": "application/json",
                    "response_body": {
                        "status": 100,
                        "description": "密码错误1次,达到3次将锁定账户"
                    }
                },
                {
                    "http_code": "200",
                    "description": "密码错误2次",
                    "media_type": "application/json",
                    "response_body": {
                        "status": 100,
                        "description": "密码错误2次,达到3次将锁定账户"
                    }
                },
                {
                    "http_code": "200",
                    "description": "密码错误3次",
                    "media_type": "application/json",
                    "response_body": {
                        "status": 100,
                        "description": "由于连续输入错误密码达到上限，账号已被锁定，请于1.0分钟后重新登录"
                    }
                }
            ]
        }
    ]
    """
    additional_info = build_default_additional_info()
    # 全局环境数据
    file_path = BASE_DIR + r"\test_data\Tools.py"
    test_env_data = {
        "base_url": "http://121.43.169.97:8081",
        "headers": {
            "Content-Type": "application/json"
        },
        # 环境变量
        "envs": {
            "correct_username": "13012341231",
            "correct_password": "test123",
        },
        "global_func": open(file_path, "r", encoding="utf-8").read(),
        "db": [
            {
                "name": "P2P",
                "type": "mysql",
                "config": {
                    "host": "121.43.169.97",
                    "port": 3306,
                    "user": "student",
                    "password": "P2P_student_2023"
                }
            }
        ]
    }
    config = {"configurable": {"thread_id": "1"}}
    res = APICaseGeneratorMainWorkflow().create_main_workflow().stream({"api_doc":api_doc,"precoditions":[],"additional_info":additional_info,"test_env_data":test_env_data},
                                                                         config=config,
                                                                         stream_mode=["messages", "custom"],
                                                                         )
    for chunk in res:
        if chunk[0] == "messages":
            print(chunk[1][0].content, end="", flush=True)
        elif chunk[0] == "custom":
            # writer() 内容每条独立一行，自动换行
            print(chunk[1], end="\n", flush=True)