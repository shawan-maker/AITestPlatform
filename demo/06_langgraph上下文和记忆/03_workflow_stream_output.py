"""
核心步骤：
1、定义状态
2、节点函数开发
3、初始化StateGraph构建器，添加节点，并建立节点的状态转换关系
4、编译为可执行图，执行流程
"""
import dotenv
import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from typing import TypedDict, Annotated
from langchain_core.output_parsers import JsonOutputParser
from langgraph.config import get_stream_writer
from langgraph.graph import StateGraph,START,END
from langgraph.types import Send
import operator

# 1、加载env文件到环境变量
dotenv.load_dotenv("../.env")


# 2、调用ChatOpenAI接口生成大模型对象
llm = ChatOpenAI(model_name=os.getenv("SI_MODEL_NAME"),
                 openai_api_key=os.getenv("SI_API_KEY"),
                 openai_api_base=os.getenv("SI_BASE_URL"))

parser = JsonOutputParser()
# 1、定义状态
class TestState(TypedDict):
    step_name: str
    description: str
    test_cases: list[dict]
    test_case: dict
    test_results: Annotated[list[str], operator.add]  # 用于收集并行执行的结果

# 2、节点函数开发
# 2.1 需求分析
def step_1(state: TestState):
    print(f"分析需求: {state['step_name']}")
    return {"step_name": "分析需求", "description": "需求分析完成"}

# 2.2 设计测试用例
def step_2(state: TestState):
    import json
    import re
    writer = get_stream_writer()
    input_prompt = """
    你是一名资深的测试工程师，请根据接口文档，设计10个测试用例
    接口文档内容为：- `Path：/member/public/login`  - `Method:POST  -参数名称： keywords、password
    状态码描述：正确用户名密码为：root/123456
    - 200：登录成功，`{"status":200,"description":"登录成功"}`
    - 100：用户不存在，`{"status":100,"description":"用户不存在"}`
    - 100：密码不能为空，`{"status":100,"description":"密码不能为空"}`
    - 100：密码错误1次，`{"status":100,"description":"密码错误1次,达到3次将锁定账户"}`
    - 100：密码错误2次，`{"status":100,"description":"密码错误2次,达到3次将锁定账户"}`
    - 100：密码错误3次，`{"status":100,"description":"由于连续输入错误密码达到上限，账号已被锁定，请于1.0分钟后重新登录"}`
    每个测试用例包含以下信息：
    - 测试用例名称 name
    - 测试用例描述 description
    - 测试用例输入参数 input_params
    - 测试用例预期结果 expect_result
      每条测试用例都返回成字典格式，所有测试用例组成一个列表返回，只返回JSON，不要有其他内容class TestState(TypedDict):
    step_name: str
    description: str
    test_cases: list[dict]  # 改为 dict 列表
    test_case: dict         # 改为 dict
    test_results: Annotated[list[str], operator.add]

    """
    response = llm.invoke(input_prompt)
    # 从LLM返回内容中提取JSON（处理markdown代码块包裹的情况）
    content = response.content
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', content, re.DOTALL)
    if json_match:
        content = json_match.group(1)
    test_cases = json.loads(content)
    writer(f"正在生成测试用例，请稍等...")
    writer(f"测试用例生成完成，包含{len(test_cases)}个测试用例")
    print(f"设计测试用例: {state['step_name']},test_cases:{test_cases}")
    return {"step_name": "设计测试用例", "description": "测试用例设计完成", "test_cases": test_cases,
            "test_results": []}


# 路由函数：为每个测试用例创建并发任务
def route_to_test_cases(state: TestState):
    return [Send("编写测试代码", {"test_case": tc}) for tc in state["test_cases"]]


# 2.3 编写测试代码（处理单个测试用例）
def step_3(state: TestState):
    # test_case = state.get("test_case", "未知用例")
    # print(f"编写测试代码: 处理测试用例 {test_case}")
    writer = get_stream_writer()
    prompt = """
        测试环境的ip地址为：192.168.1.100
        测试环境的端口号为：8080
        测试环境的协议为：http
        测试环境的域名为：192.168.1.100:8080
        测试环境的路径为：/member/public/login
        测试环境的请求方法为：POST
        测试环境的请求头为：Content-Type: application/json
        测试环境的请求体为：{"keywords":"root","password":"<PASSWORD>"}
        测试环境的预期结果为：{"status":200,"description":"登录成功"}
        将测试用例转换为测试代码，并返回测试代码(使用python+requests库实现)
    """
    test_case = llm.invoke(prompt)
    writer(f"正在生成测试代码，请稍等...")
    writer(f"测试代码生成完成，测试代码为：{test_case}")
    # 只返回需要收集的结果，不返回冲突字段
    return {"test_results": [f"{test_case}代码编写完成"]}

# 2.4 运行测试
def step_4(state: TestState):
    print(f"运行测试: {state['step_name']}")
    print(f"所有测试代码编写结果: {state.get('test_results', [])}")
    return {"step_name": "运行测试", "description": f"测试运行完成，共{len(state.get('test_results', []))}个用例"}

# 2.5 生成测试报告
def step_5(state: TestState):
    print(f"生成测试报告: {state['step_name']}")
    results = state.get("test_results", [])
    report = f"测试报告生成完成，包含{len(results)}个测试用例的结果"
    print(report)
    print(f"详细结果: {results}")
    return {"step_name": "生成测试报告", "description": report}

# 3、初始化StateGraph构建器，添加节点，并建立节点的状态转换关系
# 3.1 初始化StateGraph构建器
builder = StateGraph(TestState)
# 3.2 添加节点
builder.add_node("分析需求", step_1)
builder.add_node("设计测试用例", step_2)
builder.add_node("编写测试代码", step_3)
builder.add_node("运行测试", step_4)
builder.add_node("生成测试报告", step_5)
# 3.3 建立节点的状态转换关系
builder.add_edge(START, "分析需求")
builder.add_edge("分析需求", "设计测试用例")
# 使用路由函数实现并行执行：为每个测试用例创建并发任务
builder.add_conditional_edges("设计测试用例", route_to_test_cases)
# 并发任务完成后，聚合结果到运行测试节点
builder.add_edge("编写测试代码", "运行测试")
builder.add_edge("运行测试", "生成测试报告")
builder.add_edge("生成测试报告", END)

# 4、编译为可执行图，执行流程
# 4.1 编译为可执行图,并指定开始节点
graph = builder.compile()
res = graph.stream({"step_name": "开始执行", "description": "测试流程开始执行", "test_cases": [], "test_case": "", "test_results": []},
                   stream_mode=["messages", "custom"])

# 使用缓冲区收集同一类型的内容，实现连续输出
current_type = None
current_content = ""

for input_type, chunk in res:
    # 如果类型切换，输出之前收集的内容
    if current_type is not None and current_type != input_type and current_content:
        print(f"{current_type} —— {current_content}")
        current_content = ""
    
    current_type = input_type
    
    if input_type == "messages":
        # chunk 是元组：(AIMessageChunk, metadata_dict)
        message, metadata = chunk
        if hasattr(message, 'content'):
            # 累积内容
            current_content += message.content
    else:
        # 其他模式
        current_content += str(chunk) + "\n"

# 输出最后收集的内容
if current_type is not None and current_content:
    print(f"{current_type} —— {current_content}")

# 4.2 获取结果并绘制流程图
# image_res = graph.get_graph().draw_mermaid_png()
# with open("test_flow.png", "wb") as f:
#     f.write(image_res)