"""
定义生成测试用例需要用到的工具函数
"""
import asyncio
import json
import threading

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from service.ai_generation.common import build_default_additional_info
from service.ai_engine.shared.messages import msg
from service.ai_generation.payload_sync import (
    session_id_from_config,
    sync_api_base_payload,
    sync_functional_payload,
)
from service.core.async_utils import get_main_loop, register_main_loop, run_on_main_loop
from service.knowledge.pipeline.rag_gateway import RagGateway
from service.ai_engine.parsers.api_document_ai_parser import APIDocumentParser
from service.ai_engine.workflow.api_basecase_workflow import ApiBaseCaseGeneratorWorkflow
from service.ai_engine.workflow.api_case_main_workflow import concurrent_pre_run_base_cases
from service.ai_engine.workflow.case_generator_workflow import GenerateTestCases


# ============================================================
# 事件循环管理 —— 分离 RAG 循环和主循环
# ============================================================
# RAG 专用事件循环（无状态 HTTP 请求，可在任意独立 loop 执行）
_rag_loop = None       # 全局唯一的 RAG 事件循环
_rag_thread = None     # 运行该循环的后台线程


def _get_rag_loop():
    """获取或创建全局唯一的 RAG 专用事件循环（所有 RAG 操作共用同一个）"""
    global _rag_loop, _rag_thread
    if _rag_loop is None or not _rag_loop.is_running():
        _rag_loop = asyncio.new_event_loop()
        _rag_thread = threading.Thread(target=_rag_loop.run_forever, daemon=True)
        _rag_thread.start()
    return _rag_loop


def _run_async_safely(coro):
    """
    安全地运行异步 RAG 操作 —— 所有 RAG 操作都提交给同一个独立事件循环，
    避免 asyncio.Lock 绑定到不同循环的问题。
    仅适用于无状态 HTTP 请求（RAG），不可用于 Tortoise ORM 等绑定主 loop 的操作！
    """
    loop = _get_rag_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    # 设置超时防止死锁（5分钟）
    return future.result(timeout=300)


def _run_db_operation(coro, timeout: int = 120):
    """
    安全地运行数据库操作 —— 将协程提交回主事件循环执行。

    Tortoise ORM 的 MySQL 连接池在服务器启动时绑定到主事件循环，
    必须在同一个 loop 中执行数据库查询，否则报
    "got Future attached to a different loop" 错误。
    """
    return run_on_main_loop(coro, timeout=timeout)


# ================================生成手工/功能测试用例的工具========================================================
@tool("search_requirement",description="基于需求文档检索的工具")
def search_requirement(query:str, config: RunnableConfig):
    """
        工具作用：rag检索节点
        参数：
            query:检索的需求文档内容
    """
    project_name = config.get("context", {}).get("project_name", "")
    _lang = config.get("configurable", {}).get("language", "zh")
    writer = get_stream_writer()
    writer(msg("tools.searching_req", _lang))
    try:
        writer(msg("tools.calling_rag", _lang))
        result = _run_async_safely(RagGateway.query(project_name, query))
        print("rag检索的需求文档内容为：",result)
        if result:
            preview = result[:150] + ("..." if len(result) > 150 else "")
            writer(msg("tools.search_done_preview", _lang, preview=preview))
        else:
            writer(msg("tools.no_match_req", _lang))
        writer(msg("tools.req_search_done", _lang))
        return result or msg("tools.no_req_doc", _lang)
    except Exception as e:
        error_msg = msg("tools.search_req_error", _lang, etype=type(e).__name__, detail=str(e)[:200])
        print(error_msg)
        writer(error_msg)
        return msg("tools.search_req_fallback", _lang, etype=type(e).__name__)

@tool("generate_testcases",description="基于需求文档生成测试用例的工具")
def generate_testcases(requirement:str, config: RunnableConfig, user_prompt: str = ""):
    """
        工具作用：生成测试用例节点
        参数：
            requirement:需求文档内容（来自用户输入或search_requirement工具的输出）
            user_prompt:用户的附加要求（如数量限制"设计5条用例"、特殊场景要求等）
    """

    # 从 config 中获取语言设置
    language = config.get("configurable", {}).get("language", "zh")
    writer = get_stream_writer()
    writer(msg("tools.gen_starting", language))
    try:
        # 从 config.context 中获取项目信息
        project_name = config.get("context", {}).get("project_name", "")
        module_id = config.get("context", {}).get("module_id", "")

        from service.ai_engine.shared.language_overlay import get_language_overlay
        language_overlay = get_language_overlay(language)

        writer(msg("tools.init_workflow", language))
        workflow = GenerateTestCases().create_workflow()
        writer(msg("tools.calling_llm", language))

        # 使用 invoke() 获取完整的最终状态
        # stream() 的返回值解析复杂，直接使用 invoke() 获取最终状态更可靠
        final_state = workflow.invoke(
            {"requirement": requirement, "user_prompt": user_prompt, "language_overlay": language_overlay},
            config=config,
        )
        
        # 从最终状态中获取测试点和测试用例
        test_cases = (final_state or {}).get("test_cases", [])
        points = (final_state or {}).get("points") or (final_state or {}).get("test_points") or []

        writer(msg("tools.gen_done", language, count=len(test_cases)))

        session_id = session_id_from_config(config)
        if session_id:
            writer(msg("tools.saving_result", language))
            _run_db_operation(sync_functional_payload(session_id, final_state))
            writer(msg("tools.saved", language))
        
        return test_cases
    except Exception as e:
        error_msg = msg("tools.gen_cases_error", language, etype=type(e).__name__, detail=str(e)[:200])
        print(error_msg)
        writer(error_msg)
        raise

# ================================生成接口/自动化测试用例的工具========================================================
@tool("search_api_document",description="基于接口文档检索的工具")
def search_api_document(query: str, config: RunnableConfig):
    """
        工具作用：接口文档检索的工具，
        参数：
            query:检索的接口文档内容
    """
    project_name = config.get("context", {}).get("project_name", "")
    _lang = config.get("configurable", {}).get("language", "zh")
    writer = get_stream_writer()
    writer(msg("tools.searching_api_doc", _lang))
    try:
        result = ""
        if RagGateway.is_remote_available():
            writer(msg("tools.rag_streaming", _lang))
            for item in RagGateway.query_stream(project_name, query):
                if item is not None:
                    writer(item)
                    result += item
        else:
            writer(msg("tools.calling_rag", _lang))
            chunk = _run_async_safely(RagGateway.query(project_name, query))
            if chunk:
                writer(chunk)
                result += chunk
        if result:
            preview = result[:150] + ("..." if len(result) > 150 else "")
            writer(msg("tools.search_done_api", _lang, preview=preview))
        else:
            writer(msg("tools.no_match_api", _lang))
        writer(msg("tools.api_search_done", _lang))
        return result or msg("tools.no_api_doc", _lang)
    except Exception as e:
        error_msg = msg("tools.search_api_error", _lang, etype=type(e).__name__, detail=str(e)[:200])
        print(error_msg)
        writer(error_msg)
        return msg("tools.search_api_fallback", _lang, etype=type(e).__name__)

@tool("generate_base_cases", description="基于接口文档生成基础接口测试用例（不含预执行）")
def generate_base_cases(
    api_document: str,
    config: RunnableConfig,
    precoditions: list | None = None,
    user_prompt: str | None = None,
):
    """仅生成 api_basecase_workflow 基础用例，写入 session output_payload。"""
    # 从 config 中获取语言设置
    _lang = config.get("configurable", {}).get("language", "zh")
    writer = get_stream_writer()
    writer(msg("tools.gen_base_starting", _lang))
    try:
        res = APIDocumentParser().api_parser(api_document)
        api_doc = json.dumps(res, ensure_ascii=False, indent=4)
        writer(msg("tools.parsing_and_gen", _lang))
        from service.ai_engine.shared.language_overlay import get_language_overlay
        _overlay = get_language_overlay(_lang)
        base_workflow = ApiBaseCaseGeneratorWorkflow().create_basecase_workflow()
        base_state = base_workflow.invoke(
            {"api_doc": api_doc, "precoditions": precoditions or [], "user_prompt": user_prompt, "language_overlay": _overlay},
            config=config,
        )
        base_cases = base_state.get("api_cases") or []
        writer(msg("tools.base_gen_done", _lang, count=len(base_cases)))
        writer(msg("tools.api_gen_done", _lang))

        session_id = session_id_from_config(config)
        if session_id:
            writer(msg("tools.saving_result", _lang))
            _run_db_operation(
                sync_api_base_payload(
                    session_id,
                    base_cases=base_cases,
                    api_doc=api_doc,
                )
            )
            writer(msg("tools.saved", _lang))
        return base_cases
    except Exception as e:
        error_msg = msg("tools.gen_base_error", _lang, etype=type(e).__name__, detail=str(e)[:200])
        print(error_msg)
        writer(error_msg)
        raise

# 补充api测试用例生成所需要的环境数据的工具
@tool("load_evn_data", description="加载生成接口测试用例时的所需要的环境数据的工具")
def load_evn_data(environment_id: int):
    """加载平台测试环境数据；environment_id 为 test_environment 表主键。"""
    if not environment_id or environment_id <= 0:
        raise ValueError(
            "load_evn_data 需要有效的 environment_id（平台测试环境 ID，>0）"
        )
    precoditions = []
    additional_info = build_default_additional_info()

    from service.test_environment.variable.assembler import TestEnvDataAssembler

    # 通过 _run_db_operation 将 DB 查询安全调度回主事件循环执行，
    # 复用已有的 Tortoise ORM 连接池，绝不重新初始化/关闭连接。
    test_env_data = dict(_run_db_operation(
        TestEnvDataAssembler.get_test_env_data(environment_id, use_snapshot=False)
    ))
    test_env_data["environment_id"] = environment_id
    return {
        "precoditions": precoditions,
        "additional_info": additional_info,
        "test_env_data": test_env_data,
        "environment_id": environment_id,
    }

# 基于接口文档生成接口测试用例的工具
@tool("api_document_to_cases",description="基于接口文档生成接口测试用例的工具")
def api_document_to_cases(api_document: str,
                          config: RunnableConfig,
                          precoditions: list = None,
                          additional_info: dict = None,
                          test_env_data: dict = None,
                          environment_id: int = 0,
                          ):
    """
    基于知识库查询出来的接口文档，生成接口测试用例（与 HTTP confirm 路径一致的两阶段流程）。
    """
    env_id = environment_id or (test_env_data or {}).get("environment_id") or 0
    if env_id <= 0:
        raise ValueError(
            "api_document_to_cases 需要有效的 environment_id（请先调用 load_evn_data）"
        )

    res = APIDocumentParser().api_parser(api_document)
    api_doc = json.dumps(res, ensure_ascii=False, indent=4)

    base_workflow = ApiBaseCaseGeneratorWorkflow().create_basecase_workflow()
    _lang2 = config.get("configurable", {}).get("language", "zh")
    from service.ai_engine.shared.language_overlay import get_language_overlay as _gol
    _overlay2 = _gol(_lang2)
    base_state = base_workflow.invoke(
        {"api_doc": api_doc, "precoditions": precoditions or [], "language_overlay": _overlay2},
        config=config,
    )
    base_cases = base_state.get("api_cases") or []
    if not base_cases:
        return []

    info = additional_info or build_default_additional_info()
    _lang3 = config.get("configurable", {}).get("language", "zh")
    from service.ai_engine.shared.language_overlay import get_language_overlay as _gol3
    _overlay3 = _gol3(_lang3)
    pre_results = concurrent_pre_run_base_cases(
        base_cases,
        api_doc=api_doc,
        environment_id=env_id,
        test_env_data=test_env_data,
        additional_info=info,
        config=config,
        language_overlay=_overlay3,
    )
    return [r.api_case for r in pre_results]

if __name__ == '__main__':
    # search_requirement.invoke(input={"project_name": "tpshop", "query": "登录功能需求"})
    search_api_document.invoke(
        input={"project_name": "tpshop", "query": "获取登录模块的详细接口文档"}
    )