"""
定义生成测试用例需要用到的工具函数
"""
import asyncio
import json
import threading

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from config.settings import BASE_DIR
from rag.ragManager import RAGManager
from rag.rag_api import RAGClient
from utils.parser.api_document_ai_parser import APIDocumentParser
from workflow.api_case_main_workflow import APICaseGeneratorMainWorkflow
from workflow.case_generator_workflow import GenerateTestCases
from concurrent.futures import ThreadPoolExecutor
# ============================================================
# 🔑 单例缓存 —— 避免每次工具调用都创建新的 RAGManager 实例
# ============================================================
_rag_instances = {}  # {project_name: RAGManager实例}
_rag_client_instance = None # RAGClient 单例


# ================================rag安全调用执行方法========================================================
def _get_or_create_rag(project_name: str) -> RAGManager:
    """获取或创建 RAGManager 单例"""
    if project_name not in _rag_instances:
        _rag_instances[project_name] = RAGManager()
    return _rag_instances[project_name]


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

async def rag_search(project, req_desc: str):
    """去知识库中检索内容"""
    # 🔑 用单例而不是每次 new
    rag_manager = _get_or_create_rag(project)
    await rag_manager.init_rag(project)
    result = await rag_manager.query(req_desc)
    return result

# async def rag_search(project,req_desc: str):
#     """去知识库中检索内容"""
#     # 初始化自定义RAGManager类的对象
#     rag_manager = RAGManager()
#     # 初始化rag对象
#     await rag_manager.init_rag(project)
#     # 搜索需求文档中的具体内容
#     result = await rag_manager.query(req_desc)
#     # 将检索的需求文档，保存到state中
#     return result

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
    result = _run_async_safely(rag_search(project_name, query))
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
                            # stream_mode=["messages","custom"],
                            context={"project_name":project_name,"module_id":module_id}
                            )
    writer("【基于需求文档生成用例的服务】工具执行完毕")
    # 返回生成测试用例结果
    return response.get("test_cases",[])

# ================================生成接口/自动化测试用例的工具========================================================
def _get_or_create_rag_client() -> RAGClient:
    """获取或创建 RAGClient 单例"""
    global _rag_client_instance
    if _rag_client_instance is None:
        _rag_client_instance = RAGClient()
    return _rag_client_instance

@tool("search_api_document",description="基于接口文档检索的工具")
def search_api_document(query:str):
    """
        工具作用：接口文档检索的工具，
        参数：
            project_name:项目名称
            query:检索的接口文档内容
    """
    writer = get_stream_writer()
    writer("开始执行【接口文档检索工具】")
    # 获取单例RAG_API
    rag_client = _get_or_create_rag_client()
    # 调用rag_api中定义的查询接口
    res = rag_client.query_stream(query)
    result = ""
    # 对流式返回结果进行打印和拼接
    for item in res:
        if item is not None:
            writer(item)
            result += item
    writer("【接口文档检索工具】执行完成 ")
    return result

# 补充api测试用例生成所需要的环境数据的工具
@tool("load_evn_data", description="加载生成接口测试用例时的所需要的环境数据的工具")
def load_evn_data(environment_id: int = 0):
    precoditions = []
    additional_info = {
        "project": "p2p金融项目",
        "module": "登录模块",
        "notice": "对于不能重复使用的数据，请使用工具随机生成数据",
    }
    if environment_id:
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

        test_env_data = asyncio.run(_load())
    else:
        file_path = BASE_DIR + r"\test_data\Tools.py"
        test_env_data = {
            "base_url": "http://121.43.169.97:8081",
            "headers": {
                "Content-Type": "application/json"
            },
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
    return {"precoditions": precoditions,
            "additional_info": additional_info,
            "test_env_data": test_env_data}

# 基于接口文档生成接口测试用例的工具
@tool("api_document_to_cases",description="基于接口文档生成接口测试用例的工具")
def api_document_to_cases(api_document: str,
                          config: RunnableConfig,
                          precoditions: list = None,
                          additional_info: dict = None,
                          test_env_data: dict = None
                          ):
    """
    基于知识库查询出来的接口文档，生成接口测试用例
    :param api_document: 搜索出的接口文档
    :param precoditions: 前置依赖接口
    :param additional_info: 额外信息
    :param test_env_data: 测试环境数据
    :param config: checkpointer记忆的线程id配置
    :return:
    """
    # 1、将接口文档转换为生成接口测试用例所需的json格式
    res = APIDocumentParser().api_parser(api_document)
    api_doc = json.dumps(res, ensure_ascii=False, indent=4)
    # 2、基于json格式的json文档生成接口测试用例
    workflow = APICaseGeneratorMainWorkflow().create_main_workflow()
    res = workflow.invoke(
        {"api_doc": api_doc, "precoditions": precoditions, "additional_info": additional_info, "test_env_data": test_env_data},
        config=config
        )
    return res.get("api_run_cases")

if __name__ == '__main__':
    # search_requirement.invoke(input={"project_name": "tpshop", "query": "登录功能需求"})
    search_api_document.invoke("获取登录模块的详细接口文档")