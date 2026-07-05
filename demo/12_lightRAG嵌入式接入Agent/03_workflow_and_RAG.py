"""
父子图实现测试用例的生成：

主工作流：
  1、用户输入：需求文档 ——>
  2、分析出所有的测试点（子工作流实现）
          基于需求整理测试点 ——> 验证测试点覆盖率 ——> 对未覆盖的测试点补全 ——> 输出所有测试点
  3、基于上一个节点生成的测试点，生成特定格式的测试用例


需要共享的数据：
  1、需求文档
  2、测试点
"""
import asyncio
import os
from typing import TypedDict, List

import dotenv
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import Command
from pydantic import BaseModel
from RAG_Anything import RAGManager

# 1、加载env文件到环境变量
dotenv.load_dotenv("../.env")

# 2、调用ChatOpenAI接口生成大模型对象
llm = ChatOpenAI(model_name=os.getenv("SI_MODEL_NAME"),
                 openai_api_key=os.getenv("SI_API_KEY"),
                 openai_api_base=os.getenv("SI_BASE_URL"))


# 主工作流的状态
class State1(TypedDict):
    """主工作流的状态"""
    # 搜索词
    query: str
    # 输入需求文档
    input_requirement: str
    # 输出测试点
    test_points: list[str]
    # 输出测试用例
    test_cases: list[dict]

# 子工作流的状态
class State2(TypedDict):
    """子工作流的状态"""
    # 输入需求文档
    input_requirement: str
    # 输出测试点
    test_points: list[str]
    # 覆盖率分析报告
    coverage_report: str

# =======================================================1、子节点工作流的实现=============================================================
# 1.1、基于需求整理测试点 —— 节点1
def generate_test_points(state: State2):
    """基于需求整理测试点"""
    print("1、基于需求整理测试点：")
    # 1、获取输入的需求文档
    input_requirement = state["input_requirement"]
    # 2、编写提示词
    prompt = PromptTemplate.from_template(
        template="""
        你是一位资深测试工程师,擅长根据需求文档分析测试点，接下来需要您根据需求整理生成测试点，
       要求对该功能以“功能正常+边界+异常”为主线思维指导生成测试点，按照下面示例的格式回复
          输出示例：
              ├─ 正向验证
              │  ├─ 获取验证码后成功发送到手机号/邮箱
              │  ├─ 验证码输入正确，验证通过并进入后续流程
              │  ├─ 验证成功后验证码记录被销毁
              │  └─ 多个业务场景（绑定、找回、登录）均可正常使用验证码流程
              ├─ 边界测试
              │  ├─ 验证码长度校验（少1位/多1位/非数字）
              │  ├─ 验证码在5分钟临界点前验证仍有效
              │  ├─ 验证码5分钟后自动失效提示“验证码已失效”
              │  └─ 每分钟第1次能发，第2次提示过快，每小时第6次提示超限
              ├─ 异常处理
              ├─ 未输入验证码直接提交，提示“请输入验证码”
              ├─ 输入错误验证码，提示“验证码错误”
              ├─ 验证码过期后输入，提示“验证码已失效”
              ├─ 非法请求验证码接口（无session或业务上下文），返回异常
              └─ 网络异常/接口超时时的错误提示与重试策略
          输入的需求文档：{document}
        """)
    # 3、调用大模型，生成测试点
    chain = prompt | llm
    resp = chain.invoke({"document": input_requirement})
    # 4、获取大模型调用的结果并返回
    test_points = resp.content.split("\n")
    return {"test_points": test_points}

    
# 1.2、验证测试点覆盖率 —— 节点2
def verify_coverage(state: State2):
    """验证测试点覆盖率"""
    print("2、验证测试点覆盖率：")
    # 1、编写提示词
    prompt = PromptTemplate.from_template(
        template="""
    你是一位资深的软件测试工程师，请根据提供原始的需求文档和测试点，去分析
    原始功能文档：
    {document}
    测试点：
    {test_points}
    如果测试点覆盖了所有的功能，则回复：测试点已经全部覆盖
    如果没有全部覆盖，请给出覆盖率分析报告，并整理出未覆盖的点
    """)
    # 2、调用大模型，校验测试点覆盖率
    chain = prompt | llm
    resp = chain.invoke({"document": state["input_requirement"], "test_points": state["test_points"]})
    coverage_report = resp.content.split("\n")
    # 3、获取大模型调用的结果并返回
    return {"coverage_report": coverage_report}


# 1.3、对未覆盖的测试点补全 —— 节点3
def complete_test_points(state: State2):
    """对未覆盖的测试点补全"""
    print("3、对未覆盖的测试点补全：")
    # 1、编写提示词
    prompt = PromptTemplate.from_template(
        template="""
    你是一位资深的软件测试工程师，请根据提供原始的需求文档、测试点和覆盖率分析报告，去补充未覆盖的测试点,添加在输入的测试点后面
    原始功能文档：
    {document}
    测试点：
    {test_points}
    覆盖率报告：
    {coverage_report}
    请根据原始功能需求和测试点，补充未覆盖的测试点，并给出详细的注释
    """
    )
    # 2、调用大模型，补全测试点
    chain = prompt | llm
    resp = chain.invoke({"document": state["input_requirement"], "test_points": state["test_points"], "coverage_report": state["coverage_report"]})
    # 3、获取大模型调用的结果并返回
    return {"test_points": resp.content.split("\n")}

# 1.4、输出所有的测试点 —— 节点4
def output_test_points(state: State2):
    """输出所有的测试点"""
    print("4、输出所有测试点：")
    return {"test_points": state["test_points"]}

# 1.5 路由分发的节点
def route_dispatch(state: State2):
    """路由分发的节点"""
    if "测试点已经全部覆盖" in "\n".join(state["coverage_report"]):
        return "output_test_points"
    else:
        return "complete_test_points"

# 2.2 对子节点进行编排
builder = StateGraph(State2)
# 添加节点
builder.add_node("generate_test_points", generate_test_points)
builder.add_node("verify_coverage", verify_coverage)
builder.add_node("complete_test_points", complete_test_points)
builder.add_node("output_test_points", output_test_points)
builder.add_node("route_dispatch", route_dispatch)
# 添加边
builder.add_edge(START, "generate_test_points")
builder.add_edge("generate_test_points", "verify_coverage")
builder.add_conditional_edges("verify_coverage", route_dispatch)
builder.add_edge("complete_test_points", "verify_coverage")
builder.add_edge("output_test_points", END)
# 编辑子几点
sub_graph = builder.compile(checkpointer=True)


# =======================================================3、父节点工作流的实现=============================================================
# 3.1 生成测试用例的节点
def generate_test_cases(state: State1):
    """基于测试点生成测试用例"""
    print("1、基于测试点生成测试用例：")
    prompt = PromptTemplate.from_template(
        template='''
        你是一位资深测试工程师，请基于下面功能整理的出来的测试点，结合覆盖功能 + 探测缺陷的思维生成标准的测试用例，
        如果提供已经编写的测试用例，则在提供的测试用例基础上补充未覆盖测试点的用例
        如果未提供已经编写的测试用例，则根据测试点生成测试用例
        输出的用例，包含测试用例的八要素，：
            用例编号(case_id)
            用例名称(case_name)
            优先级(priority) 
            前置步骤(preconditions)
            测试步骤(test_steps) 
            输入数据(test_data) 
            预期结果(expected_result)
            实际结果(actual_result)
        要以json格式输出，输出格式要求为：
            [
                {{
                    "case_id": "用例编号",
                    "case_name": "用例名称",
                    "priority": "优先级",
                    "preconditions": "前置步骤",
                    "test_steps": "测试步骤",
                    "test_data": "输入数据",
                    "expected_result": "预期结果",
                    "actual_result": "实际结果"
                }},
                ...
            ]
        输入测试点：
        {test_points}
        '''
    )
    # parser = JsonOutputParser(pydantic_model=List[TestCaseModel])
    chain = prompt | llm
    res = chain.invoke({"test_points": state["test_points"]})
    print("生成测试用例结果：", res.content)
    return {"test_cases": res.content}

# 测试用例数据的解析提取类
class TestCaseModel(BaseModel):
    """测试用例数据的解析提取类"""
    case_id: str
    case_name: str
    priority: str
    preconditions: str
    test_steps: str
    test_data: str
    expected_result: str
    actual_result: str | None

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

def rag_node(state: State1):
    """rag检索节点"""
    query = state.get('query')
    result = asyncio.run(rag_search("project02",query))
    print("rag检索的需求文档内容为：",result)
    return {"input_requirement": result}

# 3.2 对主节点进行编排
main_builder = StateGraph(State1)
main_builder.add_node("rag_node", rag_node)
main_builder.add_node("create_test_points", sub_graph)
main_builder.add_node("generate_test_cases", generate_test_cases)
# 添加边
main_builder.add_edge(START, "rag_node")
main_builder.add_edge("rag_node", "create_test_points")
main_builder.add_edge("create_test_points", "generate_test_cases")
main_builder.add_edge("generate_test_cases", END)
# 编译主工作流
checkpointer=InMemorySaver()
main_graph = main_builder.compile(checkpointer=checkpointer)


if __name__ == '__main__':
    query = """请获取登录的需求描述并返回"""
    config = {"configurable":{"thread_id":"1"}}
    res = main_graph.stream({"query": query},
                            subgraphs=True,
                            config=config,
                            stream_output="messages")
    for chunk in res:
        print(chunk)