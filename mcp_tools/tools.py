"""
定义生成测试用例需要用到的工具函数
"""
import asyncio
import json
import threading

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.config import get_stream_writer


from langchain_core.runnables import RunnableConfig
from service.knowledge.pipeline.rag_gateway import RagGateway
from utils.parser.api_document_ai_parser import APIDocumentParser
from workflow.api_basecase_workflow import ApiBaseCaseGeneratorWorkflow
from workflow.api_case_main_workflow import concurrent_pre_run_base_cases
from workflow.case_generator_workflow import GenerateTestCases
from concurrent.futures import ThreadPoolExecutor

# ============================================================
# 🔑 持久化事件循环 —— 解决 Lock 绑定不同循环的问题
# ============================================================
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
    安全地运行异步函数 —— 所有 RAG 操作都提交给同一个事件循环，
    避免 asyncio.Lock 绑定到不同循环的问题。
    """
    loop = _get_rag_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    # 设置超时防止死锁（5分钟）
    return future.result(timeout=300)


# ================================生成手工/功能测试用例的工具========================================================
@tool("search_requirement",description="基于需求文档检索的工具")
def search_requirement(project_name,query:str):
    """
        工具作用：rag检索节点
        参数：
            project_name:项目名称
            query:检索的需求文档内容
    """
    writer = get_stream_writer()
    writer("开始执行【检索需求的工具】")
    result = _run_async_safely(RagGateway.query(project_name, query))
    print("rag检索的需求文档内容为：",result)
    writer("【检索需求工具】执行完成 ")
    return result

@tool("generate_testcases",description="基于需求文档生成测试用例的工具")
def generate_testcases(project_name:str, module_id:str,requirement:str,config: RunnableConfig):
    """
        工具作用：生成测试用例节点
        参数：
            project_name:项目名称
            module_id:模块id
            requirement:需求文档内容
    """

    writer = get_stream_writer()
    writer("开始执行【基于需求文档生成用例的服务】工具")
    # 创建工作流对象
    workflow = GenerateTestCases().create_workflow()
    # 配置工作流并执行
    response = workflow.invoke({"requirement": requirement},
                            subgraphs=True,
                            config=config,
                            )
    writer("【基于需求文档生成用例的服务】工具执行完毕")
    # 返回生成测试用例结果
    return response.get("test_cases",[])

# ================================生成接口/自动化测试用例的工具========================================================
@tool("search_api_document",description="基于接口文档检索的工具")
def search_api_document(project_name: str, query: str):
    """
        工具作用：接口文档检索的工具，
        参数：
            project_name:项目名称
            query:检索的接口文档内容
    """
    writer = get_stream_writer()
    writer("开始执行【接口文档检索工具】")
    result = ""
    if RagGateway.is_remote_available():
        for item in RagGateway.query_stream(project_name, query):
            if item is not None:
                writer(item)
                result += item
    else:
        chunk = _run_async_safely(RagGateway.query(project_name, query))
        if chunk:
            writer(chunk)
            result += chunk
    writer("【接口文档检索工具】执行完成 ")
    return result

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
    import asyncio

    from service.core.database import close_db, init_db
    from service.test_environment.variable.assembler import TestEnvDataAssembler

    async def _load():
        await init_db()
        try:
            return await TestEnvDataAssembler.get_test_env_data(
                environment_id,
                use_snapshot=True,
                merge_debug=True,
            )
        finally:
            await close_db()

    test_env_data = dict(asyncio.run(_load()))
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
    base_state = base_workflow.invoke(
        {"api_doc": api_doc, "precoditions": precoditions or []},
        config=config,
    )
    base_cases = base_state.get("api_cases") or []
    if not base_cases:
        return []

    info = additional_info or build_default_additional_info()
    pre_results = concurrent_pre_run_base_cases(
        base_cases,
        api_doc=api_doc,
        environment_id=env_id,
        test_env_data=test_env_data,
        additional_info=info,
        config=config,
    )
    return [r.api_case for r in pre_results]

if __name__ == '__main__':
    # search_requirement.invoke(input={"project_name": "tpshop", "query": "登录功能需求"})
    search_api_document.invoke(
        input={"project_name": "tpshop", "query": "获取登录模块的详细接口文档"}
    )