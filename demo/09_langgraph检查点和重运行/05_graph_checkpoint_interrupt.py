"""
核心步骤：
1、定义状态
2、节点函数开发
3、初始化StateGraph构建器，添加节点，并建立节点的状态转换关系
4、编译为可执行图，执行流程
"""
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph,START,END
from langgraph.types import interrupt, Command


# 1、定义状态
class TestState(TypedDict):
    step_name: str
    description: str

# 2、节点函数开发
# 2.1 需求分析
def step_1(state: TestState):
    print(f"1.分析需求: {state['step_name']}")
    return {"step_name": "分析需求", "description": "需求分析完成"}

# 2.2 设计测试用例
def step_2(state: TestState):
    print(f"2.设计测试用例: {state['step_name']}")
    return {"step_name": "设计测试用例", "description": "测试用例设计完成"}

# 2.3 编写测试代码
def step_3(state: TestState):
    print(f"3.编写测试代码: {state['step_name']}")
    value = interrupt("已当前代码生成，请判断是否正确？[y/n]")
    return {"step_name": "编写测试代码", "description": "测试代码编写完成","interrup":value}

# 2.4 运行测试
def step_4(state: TestState):
    print(f"4.运行测试: {state['step_name']}")
    return {"step_name": "运行测试", "description": "测试运行完成"}

# 2.5 生成测试报告
def step_5(state: TestState):
    print(f"5.生成测试报告: {state['step_name']}")
    return {"step_name": "生成测试报告", "description": "测试报告生成完成"}

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

# 定义检查点
checkpointer = InMemorySaver()

# 4、编译为可执行图，执行流程
# 4.1 编译为可执行图,并指定开始节点
graph = builder.compile(checkpointer=checkpointer)
config = {"configurable":{"thread_id":"1"}}
res = graph.invoke({"step_name": "开始执行", "description": "测试流程开始执行"},config=config)
print("=================================打印工作流内容===========================================")
print(res,type(res))

while True:
    if "__interrupt__" in res:
        prompt = res.get("__interrupt__")[0].value
        value = input(prompt)
        if value == "n":
            print("重新生成代码")
            res = graph.invoke(Command(goto="编写测试代码"), config=config)
        else:
            res = graph.invoke(Command(resume="不用重新生成"), config=config)
    else:
        break