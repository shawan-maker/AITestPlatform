"""
核心步骤：
1、定义状态
2、节点函数开发
3、初始化StateGraph构建器，添加节点，并建立节点的状态转换关系
4、编译为可执行图，执行流程
"""
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph,START,END
from langgraph.types import Send
import operator


# 1、定义状态
class TestState(TypedDict):
    step_name: str
    description: str
    test_cases: list[str]
    test_case: str
    test_results: Annotated[list[str], operator.add]  # 用于收集并行执行的结果

# 2、节点函数开发
# 2.1 需求分析
def step_1(state: TestState):
    print(f"分析需求: {state['step_name']}")
    return {"step_name": "分析需求", "description": "需求分析完成"}

# 2.2 设计测试用例
def step_2(state: TestState):
    test_cases = [f"测试用例{i}" for i in range(5)]
    print(f"设计测试用例: {state['step_name']},test_cases:{test_cases}")
    return {"step_name": "设计测试用例", "description": "测试用例设计完成", "test_cases": test_cases, "test_results": []}

# 路由函数：为每个测试用例创建并发任务
def route_to_test_cases(state: TestState):
    return [Send("编写测试代码", {"test_case": tc}) for tc in state["test_cases"]]

# 2.3 编写测试代码（处理单个测试用例）
def step_3(state: TestState):
    test_case = state.get("test_case", "未知用例")
    print(f"编写测试代码: 处理测试用例 {test_case}")
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
res = graph.invoke({"step_name": "开始执行", "description": "测试流程开始执行", "test_cases": [], "test_case": "", "test_results": []})
print(res,type(res))

# 4.2 获取结果并绘制流程图
image_res = graph.get_graph().draw_mermaid_png()
with open("test_flow.png", "wb") as f:
    f.write(image_res)