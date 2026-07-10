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
from typing import TypedDict, List

from langchain_core.output_parsers import JsonOutputParser
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from pydantic import BaseModel

from service.ai_engine.prompts.workflow import generate_test_cases_prompt, verify_coverage_prompt, generate_test_points_prompt, complete_test_points_prompt
from service.ai_engine.shared.language_overlay import get_language_overlay, is_coverage_complete
from service.ai_engine.shared.messages import msg, lang_from_overlay
from service.core.settings import llm
from service.ai_generation.common import format_user_prompt_section
from service.core.settings import MAX_COMPLETE_TEST_POINTS
from service.ai_engine.parsers.api_document_ai_parser import safe_structure_parser


# 主工作流的状态
class State1(TypedDict):
    """主工作流的状态"""
    # 输入需求文档
    requirement: str
    # 用户附加要求
    user_prompt: str | None
    # 输出测试点
    points: List[dict]
    # 输出测试用例
    test_cases: list[dict]
    # 语言覆盖指令（空串=中文，英文指令=英文输出）
    language_overlay: str

# 子工作流的状态
class State2(TypedDict):
    """子工作流的状态"""
    input_requirement: str
    user_prompt: str | None
    test_points: list[dict]
    coverage_report: str
    complete_round: int
    max_test_points: int | None  # 最大测试点数量（从用户提示词中解析，None 表示不限制）
    language_overlay: str

class TestPointModel(BaseModel):
    """定义测试点类"""
    # 用例类型
    type: str
    # 用例维度
    dimension: str
    # 用例测试点
    test_point: str

class TestCaseModel(BaseModel):
    """定义测试用例类"""
    case_id: str
    case_name: str
    priority: str
    type:str
    dimension: str
    preconditions: str
    test_steps: str
    test_data: str
    expected_result: str
    actual_result: str

# =======================================================1、子节点工作流的实现=============================================================
class GeneratePoints(BaseModel):
    """定义子工作流的类（生成测试点）"""
    # 1.1、基于需求整理测试点 —— 节点1
    def generate_test_points(self,state: State2):
        """基于需求整理测试点"""
        writer = get_stream_writer()
        _lang = lang_from_overlay(state.get("language_overlay", ""))
        writer(msg("wf.node1_start", _lang))
        # 1、获取输入的需求文档
        input_requirement = state["input_requirement"]
        language_overlay = state.get("language_overlay", "")
        _lang = "en" if language_overlay else "zh"
        user_prompt_section = format_user_prompt_section(state.get("user_prompt"), _lang)
        max_test_points = state.get("max_test_points")  # 可能为 None，表示不限制
        language_overlay = state.get("language_overlay", "")
        # 2、编写提示词
        prompt = generate_test_points_prompt.prompt
        # 配置测试点解释器
        parser = JsonOutputParser(pydantic_schema=List[TestPointModel])
        # 3、调用大模型，生成测试点（传入 max_test_points_section 控制数量）
        resp = safe_structure_parser(
            prompt,
            llm,
            parser,
            {
                "document": input_requirement,
                "user_prompt_section": user_prompt_section,
                "max_test_points_section": generate_test_points_prompt.get_max_test_points_section(max_test_points),
                "max_test_points_requirement": generate_test_points_prompt.get_max_test_points_requirement(max_test_points),
                "language_overlay": language_overlay,
            },
        )
        # 4、获取大模型调用的结果并返回（不再做截断，由 prompt 控制数量）
        writer(msg("wf.node1_done", _lang, count=len(resp)))
        return {"test_points": resp}


    # 1.2、验证测试点覆盖率 —— 节点2
    def verify_coverage(self,state: State2):
        """验证测试点覆盖率"""
        writer = get_stream_writer()
        _lang = lang_from_overlay(state.get("language_overlay", ""))
        max_test_points = state.get("max_test_points")
        current_count = len(state.get("test_points") or [])
        # 仅当已达数量上限时跳过（还有空间则正常验证，允许补全）
        if max_test_points is not None and current_count >= max_test_points:
            writer(msg("wf.node2_skip", _lang, current=current_count, max=max_test_points))
            return {"coverage_report": ["测试点已经全部覆盖"]}
        writer(msg("wf.node2_start", _lang))
        language_overlay = state.get("language_overlay", "")
        user_prompt_section = format_user_prompt_section(state.get("user_prompt"), _lang)
        language_overlay = state.get("language_overlay", "")
        # 1、编写提示词
        prompt = verify_coverage_prompt.prompt
        # 2、调用大模型，校验测试点覆盖率
        chain = prompt | llm
        resp = chain.invoke(
            {
                "document": state["input_requirement"],
                "test_points": state["test_points"],
                "user_prompt_section": user_prompt_section,
                "language_overlay": language_overlay,
            }
        )
        coverage_report = resp.content.split("\n")
        writer(msg("wf.node2_done", _lang))
        # 3、获取大模型调用的结果并返回
        return {"coverage_report": coverage_report}


    # 1.3、对未覆盖的测试点补全 —— 节点3
    def complete_test_points(self,state: State2):
        """对未覆盖的测试点补全"""
        writer = get_stream_writer()
        _lang = lang_from_overlay(state.get("language_overlay", ""))
        writer(msg("wf.node3_start", _lang))
        language_overlay = state.get("language_overlay", "")
        user_prompt_section = format_user_prompt_section(state.get("user_prompt"), _lang)
        max_test_points = state.get("max_test_points")  # 可能为 None，表示不限制
        language_overlay = state.get("language_overlay", "")
        # 1、编写提示词
        prompt = complete_test_points_prompt.prompt
        # 配置测试点解释器
        parser = JsonOutputParser(pydantic_schema=List[TestPointModel])
        # 2、调用大模型，补全测试点（传入 max_test_points_section 控制数量）
        resp = safe_structure_parser(
            prompt,
            llm,
            parser,
            {
                "document": state["input_requirement"],
                "test_points": state["test_points"],
                "coverage_report": state["coverage_report"],
                "user_prompt_section": user_prompt_section,
                "max_test_points_section": complete_test_points_prompt.get_max_test_points_section(max_test_points),
                "language_overlay": language_overlay,
            },
        )
        
        # 如果 max_test_points 有值，则限制补充的测试点数量，使总数不超过max_test_points
        existing = state.get("test_points", [])
        if not isinstance(existing, list):
            existing = []
        current_count = len(existing)
        
        # 只在 max_test_points 有值时限制数量
        if max_test_points is not None:
            remaining_slots = max(0, max_test_points - current_count)
            # 只取需要补充的测试点数量
            if len(resp) > remaining_slots:
                resp = resp[:remaining_slots]
        
        writer(msg("wf.node3_done", _lang, added=len(resp), total=current_count + len(resp)))
        # 拼接已有测试点和补充的测试点
        test_points = existing + resp
        complete_round = int(state.get("complete_round") or 0) + 1
        return {"test_points": test_points, "complete_round": complete_round}

    # 1.4、输出所有的测试点 —— 节点4
    def output_test_points(self,state: State2):
        """输出所有的测试点"""
        writer = get_stream_writer()
        test_points = state["test_points"]
        # 不在子工作流中输出完成标志，改在父工作流中输出
        return {"test_points": test_points}

    # 1.5 路由分发的节点
    def route_dispatch(self,state: State2):
        """路由分发的节点"""
        _lang = lang_from_overlay(state.get("language_overlay", ""))
        complete_round = int(state.get("complete_round") or 0)
        test_points_count = len(state.get("test_points") or [])
        max_test_points = state.get("max_test_points")
        
        # 如果达到最大补充轮数，停止
        if complete_round >= MAX_COMPLETE_TEST_POINTS:
            return "output_test_points"
        # 如果覆盖率报告显示已全部覆盖，停止（同时检查中英文标记）
        if is_coverage_complete("\n".join(state["coverage_report"])):
            return "output_test_points"
        # [FIX-问题5] 如果用户指定了数量限制且已有测试点，跳过补全避免总数超限
        if max_test_points is not None and test_points_count > 0:
            writer(msg("wf.count_control", _lang, max=max_test_points, current=test_points_count))
            return "output_test_points"
        return "complete_test_points"

    # 1.6 编排生成测试点的工作流
    def create_workflow(self):
        # 2.2 对子节点进行编排
        builder = StateGraph(State2)
        # 添加节点
        builder.add_node("generate_test_points", self.generate_test_points)
        builder.add_node("verify_coverage", self.verify_coverage)
        builder.add_node("complete_test_points", self.complete_test_points)
        builder.add_node("output_test_points", self.output_test_points)
        builder.add_node("route_dispatch", self.route_dispatch)
        # 添加边
        builder.add_edge(START, "generate_test_points")
        builder.add_edge("generate_test_points", "verify_coverage")
        builder.add_conditional_edges("verify_coverage", self.route_dispatch)
        builder.add_edge("complete_test_points", "verify_coverage")
        builder.add_edge("output_test_points", END)
        # 编辑子几点
        sub_graph = builder.compile(checkpointer=True)
        return sub_graph


# =======================================================3、父节点工作流的实现=============================================================
class GenerateTestCases:
    """定义父工作流的类（生成测试用例）"""
    def __init__(self):
        self.sub_graph = GeneratePoints().create_workflow()

    # 3.1 生成测试点（调用子工作流实现）
    def create_test_points(self,state: State1):
        """创建测试点"""
        writer = get_stream_writer()
        _lang = lang_from_overlay(state.get("language_overlay", ""))
        writer(msg("wf.node3_1_start", _lang))

        # 解析用户提示词中的数量要求（如"5条"、"10个"、"5个测试用例"等）
        max_test_points = None  # 默认不限制
        user_prompt = state.get("user_prompt") or ""
        import re
        # 支持匹配中英文：5条、5个、5个测试点、5 test cases、10 test points
        search_text = user_prompt if user_prompt else (state.get("requirement") or "")
        match = re.search(r'(\d+)\s*(条|个|test\s*cases?|test\s*points?|cases?)(测试用例|测试点|用例)?', search_text, re.IGNORECASE)
        if match:
            max_test_points = int(match.group(1))

        # 1、调用子工作流
        res = self.sub_graph.invoke(
            {
                "input_requirement": state["requirement"],
                "user_prompt": state.get("user_prompt"),
                "complete_round": 0,
                "max_test_points": max_test_points,  # 可能为 None
                "language_overlay": state.get("language_overlay", ""),
            }
        )
        # 在父工作流中输出完成标志，确保只输出一次且时机正确
        writer(msg("wf.node3_1_done", _lang, count=len(res['test_points'])))
        writer(msg("wf.node3_1_end", _lang))
        # 2、获取子工作流的结果并返回给父工作流
        return {"points": res["test_points"]}

    # 3.2 生成测试用例的节点
    def generate_test_cases(self, state: State1):
        """基于测试点生成测试用例"""
        writer = get_stream_writer()
        _lang = lang_from_overlay(state.get("language_overlay", ""))
        writer(msg("wf.node3_2_start", _lang))
        language_overlay = state.get("language_overlay", "")
        _lang = "en" if language_overlay else "zh"
        user_prompt_section = format_user_prompt_section(state.get("user_prompt"), _lang)
        language_overlay = state.get("language_overlay", "")

        # 解析用户要求的最大测试用例数量
        max_test_points = None  # 默认不限制
        user_prompt = state.get("user_prompt") or ""
        import re
        search_text = user_prompt if user_prompt else (state.get("requirement") or "")
        match = re.search(r'(\d+)\s*(条|个|test\s*cases?|test\s*points?|cases?)(测试用例|测试点|用例)?', search_text, re.IGNORECASE)
        if match:
            max_test_points = int(match.group(1))

        # 不再截断测试点数量，由 prompt 控制
        points = state["points"]

        # 使用动态 prompt
        prompt = generate_test_cases_prompt.prompt

        parser = JsonOutputParser(pydantic_schema=List[TestCaseModel])
        resp = safe_structure_parser(
            prompt,
            llm,
            parser,
            {
                "points": points,
                "user_prompt_section": user_prompt_section,
                "max_test_points_section": generate_test_cases_prompt.get_max_test_points_section(max_test_points),
                "max_test_points_requirement": generate_test_cases_prompt.get_max_test_points_requirement(max_test_points),
                "language_overlay": language_overlay,
            },
        )
        # 不再截断用例数量，由 prompt 控制
        writer(msg("wf.node3_2_done", _lang, count=len(resp)))
        return {"test_cases": resp}

    def create_workflow(self):
        """编排生成测试用例的工作流"""
        # 3.2 对主节点进行编排
        main_builder = StateGraph(State1)
        main_builder.add_node("create_test_points", self.create_test_points)
        main_builder.add_node("generate_test_cases", self.generate_test_cases)
        # 添加边
        main_builder.add_edge(START, "create_test_points")
        main_builder.add_edge("create_test_points", "generate_test_cases")
        main_builder.add_edge("generate_test_cases", END)
        # 编译主工作流
        checkpointer=InMemorySaver()
        main_graph = main_builder.compile(checkpointer=checkpointer)
        return main_graph


if __name__ == '__main__':
    import sys

    from service.core import settings as core_config

    if not core_config.AITESTPLATFORM_ALLOW_WORKFLOW_MAIN:
        print("Set AITESTPLATFORM_ALLOW_WORKFLOW_MAIN=1 to run this workflow demo")
        sys.exit(0)
    input_requirement = """功能说明文档：
#### 📌 F1.1 用户注册
##### 🧩 功能背景
新用户通过注册方式创建账户，支持邮箱/用户名+密码的注册方式。

##### 🚶 主流程
1. 用户打开注册页，填写注册信息
2. 系统校验格式与唯一性（用户名、邮箱）
3. 提交注册，后台创建账户，初始状态为“正常”
4. 注册成功后自动登录并跳转首页

##### ⚠️ 异常流程
- 邮箱/用户名已被注册：提示“已存在”
- 两次密码不一致：提示用户重新输入

##### 📌 状态规则
- 新用户状态为 “正常”
- 注册时间记录为创建时间，头像为默认图

##### 📌 业务规则
- 用户名唯一，支持 4~20 位字母数字组合
- 密码长度不少于 6 位
- 邮箱必须符合格式 `xxx@xxx.xx`"""
    config = {"configurable":{"thread_id":"1"}}
    res = GenerateTestCases().create_workflow().stream({"requirement": input_requirement},
                            subgraphs=True,
                            config=config,
                            stream_mode=["messages","custom"],
                            )
    print("=========================")
    # for chunk in res:
    #     print(chunk)
    for chunk in res:
        if chunk[1] == "custom":
            print()
            print(chunk[2])
        elif chunk[1] == "messages":
            print(chunk[2][0].content,end="",flush=True)