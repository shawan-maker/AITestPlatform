"""
定义生成测试用例需要用到的工具函数
"""
import asyncio
from langchain_core.tools import tool
from langgraph.config import get_stream_writer

from demo.CaseGenerateAgent.RAG_Anything import RAGManager
from demo.CaseGenerateAgent.workflow.case_generate_workflow import GenerateTestCases


async def rag_search(project,req_desc: str):
    """去知识库中检索内容"""
    # 初始化自定义RAGManager类的对象
    rag_manager = RAGManager()
    # 初始化rag对象
    await rag_manager.init_rag(project)
    # 搜索需求文档中的具体内容
    result = await rag_manager.query(req_desc)
    # 将检索的需求文档，保存到state中
    return result

@tool("search_requirement",description="检索需求文档")
def search_requirement(query:str):
    """rag检索节点"""
    result = asyncio.run(rag_search("project02",query))
    print("rag检索的需求文档内容为：",result)
    return {"input_requirement": result}

@tool("generate_testcases",description="生成测试用例")
def generate_testcases(requirement:str):
    """生成测试用例节点"""
    writer = get_stream_writer()
    writer("开始执行【基于需求文档生成用例的服务】工具")
    # 创建工作流对象
    workflow = GenerateTestCases().create_workflow()
    # 配置工作流并执行
    config = {"configurable": {"thread_id": "1"}}
    response = workflow.invoke({"requirement": requirement},
                            subgraphs=True,
                            config=config,
                            stream_output=["messages","custom"])
    writer("【基于需求文档生成用例的服务】工具执行完毕")
    # 返回生成测试用例结果
    return response.get("test_cases")


if __name__ == '__main__':
    search_requirement.invoke("请获取登录的需求描述并返回")