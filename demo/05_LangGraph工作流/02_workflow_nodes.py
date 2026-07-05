"""
核心步骤：
1、定义节点参数（状态、上下文、配置）
    在 LangGraph 中，节点 可以 接受以下参数的 Python 函数（同步或异步）：
    ● state：图形的状态
    ● config：包含配置信息和跟踪信息（如RunnableConfigthread_idtags）
    ● runtime：包含运行时上下文context和其他信息（如 Runtimestorestream_writer）
        ———— context 是只读的，不应该用来传递需要在节点间修改的数据。如果数据需要被节点修改并在后续节点中使用，必须放在 state 里。
        ———— state 和 context 的职责区分：state 是可变的、节点间传递的工作数据；context 是只读的、全局的运行时信息（如当前用户、请求头等）。
2、节点函数开发
3、初始化StateGraph构建器，添加节点，并建立节点的状态转换关系
4、编译为可执行图，执行流程
"""
from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph,START,END
from dataclasses import dataclass
from langgraph.runtime import Runtime


# 1、定义节点参数
# 1.1 定义节点的状态
class TestState(TypedDict):
    step_name: str
    description: str
    test_name: str
    test_data: str
    test_result: str
    test_time: str

# 1.2 定义节点的上下文数据

@dataclass
class TestContext:
    test_name: str
    test_data: str
    test_result: str
    test_time: str

# 2、节点函数开发
# 2.1 需求分析
def step_1(state: TestState):
    print(f"分析需求: {state['step_name']}")
    return {"step_name": "分析需求", "description": "需求分析完成"}

# 2.2 设计测试用例
def step_2(state: TestState,runtime: Runtime[TestContext]):
    print(f"设计测试用例: {state['step_name']},runtime:{runtime}")
    return {"step_name": "设计测试用例", "description": "测试用例设计完成", "test_name": runtime.context.test_name, "test_data": runtime.context.test_data, "test_result": runtime.context.test_result, "test_time": runtime.context.test_time}

# 2.3 编写测试代码
def step_3(state: TestState):
    print(f"编写测试代码: {state['step_name']}")
    return {"step_name": "编写测试代码", "description": "测试代码编写完成"}

# 2.4 运行测试
def step_4(state: TestState,runtime: Runtime[TestContext],config: RunnableConfig):
    print(f"运行测试: {state['step_name']},runtime:{runtime},config:{config}")
    return {"step_name": "运行测试", "description": "测试运行完成", "test_name": "测试用例1", "test_data": "测试数据1", "test_result": config.get("configurable").get("result"), "test_time": "2025-06-01 12:00:00"}

# 2.5 生成测试报告
def step_5(state: TestState,runtime: Runtime[TestContext]):
    print(f"生成测试报告: {state['step_name']},runtime:{runtime}")
    return {"step_name": "生成测试报告", "description": "测试报告生成完成", "test_name": runtime.context.test_name, "test_data": runtime.context.test_data, "test_result": runtime.context.test_result, "test_time": runtime.context.test_time}

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
builder.add_edge("设计测试用例", "编写测试代码")
builder.add_edge("编写测试代码", "运行测试")
builder.add_edge("运行测试", "生成测试报告")
builder.add_edge("生成测试报告", END)

# 4、编译为可执行图，执行流程
# 4.1 编译为可执行图,并指定开始节点
graph = builder.compile()
res = graph.invoke(
    {"step_name": "开始执行", "description": "测试流程开始执行"},
    config={"configurable": {"result":True}},
    context=TestContext(
        test_name="测试用例1",
        test_data="测试数据1",
        test_result="无",
        test_time="无",
    )
)
print(res,type(res))

# 4.2 获取结果并绘制流程图
image_res = graph.get_graph().draw_mermaid_png()
with open("test_flow.png", "wb") as f:
    f.write(image_res)



