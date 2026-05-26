"""
API接口测试用例生成工作流:
    1、用户输入：
        (1)测试的API接口文档
        (2)该接口调用前置接口的依赖关系(A-B-C)
        (3)测试环境中实现准备的测试数据： ${变量名称}进行占位处理
    2、加载项目的数据库信息和自定义脚本工具
        （1）加载可用的工具函数
        （2）如果要在前后置脚本中生成数据库查询和校验的脚本（提供数据库的表结构信息）
    3、生成测试用例：
        （1）生成基础的测试用例（测试点）
        （2）验证覆盖率
        （3）补充生成测试用例（测试点）
        （4）基于生成的基础用例，并发生成前面封装的执行器可以直接执行的结构化用例(封装为langgraph的子图)
            (a) 可以使用langgraph中的send实现并发
            (b) 对于生成的结构化用例进行预执行（执行失败用例直接标记），执行错误的用例再重新生成（连接错误三次也直接进行标记）
        （5）输出可执行的用例，保存到数据库
"""
import operator
from typing import TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer
from langgraph.graph import StateGraph,START,END
from pydantic import BaseModel, Field

from config.prompts.api_workflow.api_verify_courage_prompt import api_coverage_check_prompt
from config.prompts.api_workflow.complete_api_basecase_prompt import complete_api_basecase_prompt
from config.settings import MAX_BASECASE_REGENERATE_COUNT, llm
from config.prompts.api_workflow.api_basecase_generator_prompt import api_basecase_generator_prompt
from langchain_core.output_parsers import JsonOutputParser
from typing import List,Annotated

from utils.parser.api_document_ai_parser import safe_structure_parser

checkpointer=InMemorySaver()

# 定义工作流的数据状态
class StateNode(TypedDict):
    api_doc: str  # API接口文档
    project_name: str  # 项目名称
    module_name: str  # 模块名称
    precoditions: list[str]  # 前置执行依赖接口的调用顺序
    api_cases: Annotated[List, operator.add]  # 生成的测试用例
    api_cases_check_report: str  # 覆盖率验证报告
    env_config: dict  # 测试环境配置
    basecase_regenerate_count: int  # 已执行的补充生成次数

class BaseCaseModel(BaseModel):
    name: str = Field(description="测试用例名称")
    steps: list[str] = Field(description="测试用例步骤")
    dependencies: list[str] = Field(description="前置依赖的接口列表")
    expected: list[str] = Field(description="预期结果的断言列表")
 
class ApiBaseCaseGeneratorWorkflow:
    """API接口测试用例生成工作流： 基于API接口文档生成基础的测试用例（测试点）"""
    # 1、生成基础的测试用例（测试点）
    def generate_basecase(self,state:StateNode):
        """生成基础的接口测试用例（测试点）"""
        # 1、获取API接口文档和对应的依赖接口
        writer = get_stream_writer()
        writer("【开始执行节点】 1、生成api基础测试用例：")
        api_doc = state.get("api_doc")
        precoditions = state.get("precoditions")
        # 2、调用AI模型生成基础的测试用例
        parser = JsonOutputParser(pydantic_schema=List[BaseCaseModel])
        resp = safe_structure_parser(api_basecase_generator_prompt,llm,parser,{"api_doc":api_doc,"precoditions":precoditions})
        writer("【执行节点完成】 1、生成api基础测试用例：")
        # 3、返回基础的测试用例
        return {"api_cases": resp}

    # 2、验证覆盖率
    def verify_coverage(self,state:StateNode):
        """验证覆盖率"""
        # 1、获取API接口文档和对应的依赖接口
        writer = get_stream_writer()
        writer("【开始执行节点】 2、验证api基础测试用例覆盖率：")
        api_doc = state.get("api_doc")
        precoditions = state.get("precoditions")
        api_cases = state.get("api_cases")
        # 2、调用AI模型生成基础的测试用例
        chain = api_coverage_check_prompt | llm
        resp = chain.invoke({"api_doc":api_doc,"precoditions":precoditions,"api_cases":api_cases})
        coverage_report = resp.content.split("\n")
        writer("【执行节点完成】 2、验证api基础测试用例覆盖率：")
        # 3、返回覆盖率的验证报告
        return {"api_cases_check_report": coverage_report}

    # 3、补充生成api测试用例（测试点）
    def complete_basecase(self,state:StateNode):
        """补充生成api测试用例（测试点）"""
        # 1、获取API接口文档和对应的依赖接口
        writer = get_stream_writer()
        writer("【开始执行节点】 3、补充生成api基础测试用例：")
        api_doc = state.get("api_doc")
        precoditions = state.get("precoditions")
        api_cases = state.get("api_cases")
        api_cases_check_report = state.get("api_cases_check_report")
        # 2、调用AI模型生成基础的测试用例
        parser = JsonOutputParser(pydantic_schema=List[BaseCaseModel])
        resp = safe_structure_parser(complete_api_basecase_prompt,llm,parser,{"api_doc":api_doc,"precoditions":precoditions,"api_cases":api_cases,"api_cases_check_report":api_cases_check_report})
        writer("【执行节点完成】 3、补充生成api基础测试用例：")
        count = state.get("basecase_regenerate_count", 0) + 1
        writer(f"基础用例补充生成次数：{count}/{MAX_BASECASE_REGENERATE_COUNT}")
        return {"api_cases": resp, "basecase_regenerate_count": count}

    # 1.4、输出所有的测试点
    def output_basecase(self,state: StateNode):
        """输出所有的测试点"""
        writer = get_stream_writer()
        writer("【开始执行节点】 4、输出所有基础测试用例")
        writer(state["api_cases"])
        # 此处不能再返回一个{"api_cases": state["api_cases"]}，因为会导致operator.add 导致重复追加！
        # return {"api_cases": state["api_cases"]}
        return {}

    # 1.5 路由分发的节点
    def route_dispatch(self, state: StateNode):
        """路由分发的节点"""
        report = state.get("api_cases_check_report") or []
        count = state.get("basecase_regenerate_count", 0)
        if "已经覆盖全部测试点" in "\n".join(report):
            return "output_basecase"
        if count >= MAX_BASECASE_REGENERATE_COUNT:
            writer = get_stream_writer()
            writer(
                f"已达基础用例最大补充生成次数({MAX_BASECASE_REGENERATE_COUNT})，停止补充"
            )
            return "output_basecase"
        return "complete_basecase"

    def create_basecase_workflow(self):
        """创建工作流"""
        # 1、创建一个graph对象
        builder = StateGraph(StateNode)
        # 2、添加节点
        # 2.1 添加节点：生成基础的测试用例
        builder.add_node("generate_basecase", self.generate_basecase)
        # 2.2 添加节点：验证覆盖率
        builder.add_node("verify_coverage", self.verify_coverage)
        # # 2.3 添加节点：补充生成测试用例（测试点）
        builder.add_node("complete_basecase",self.complete_basecase)
        # # 2.4 添加节点：输出基础测试用例
        builder.add_node("output_basecase",self.output_basecase)
        # 2.5 添加节点：路由分发
        builder.add_node("route_dispatch",self.route_dispatch)
        # 3、建立节点之间的状态转换关系
        builder.add_edge(START,"generate_basecase")
        builder.add_edge("generate_basecase","verify_coverage")
        builder.add_conditional_edges("verify_coverage",self.route_dispatch)
        builder.add_edge("complete_basecase","verify_coverage")
        builder.add_edge("output_basecase",END)
        # 4、编译为可执行图并返回
        graph = builder.compile(checkpointer=checkpointer)
        return graph

if __name__ == '__main__':
    api_doc = """[
    {
        "path": "/member/public/login",
        "method": "POST",
        "summary": "登录",
        "parameters": {
            "header": [
                {
                    "name": "Content-Type",
                    "type": "string",
                    "description": "",
                    "required": true
                }
            ],
            "path": [],
            "query": []
        },
        "requestBody": {
            "content_type": "application/x-www-form-urlencoded",
            "body": [
                {
                    "name": "keywords",
                    "type": "string",
                    "description": "手机号",
                    "required": true
                },
                {
                    "name": "password",
                    "type": "string",
                    "description": "密码",
                    "required": true
                }
            ]
        },
        "responses": [
            {
                "http_code": "200",
                "description": "登录成功",
                "media_type": "application/json",
                "response_body": {
                    "status": 200,
                    "description": "登录成功"
                }
            },
            {
                "http_code": "200",
                "description": "用户不存在",
                "media_type": "application/json",
                "response_body": {
                    "status": 100,
                    "description": "用户不存在"
                }
            },
            {
                "http_code": "200",
                "description": "密码不能为空",
                "media_type": "application/json",
                "response_body": {
                    "status": 100,
                    "description": "密码不能为空"
                }
            },
            {
                "http_code": "200",
                "description": "密码错误1次",
                "media_type": "application/json",
                "response_body": {
                    "status": 100,
                    "description": "密码错误1次,达到3次将锁定账户"
                }
            },
            {
                "http_code": "200",
                "description": "密码错误2次",
                "media_type": "application/json",
                "response_body": {
                    "status": 100,
                    "description": "密码错误2次,达到3次将锁定账户"
                }
            },
            {
                "http_code": "200",
                "description": "密码错误3次",
                "media_type": "application/json",
                "response_body": {
                    "status": 100,
                    "description": "由于连续输入错误密码达到上限，账号已被锁定，请于1.0分钟后重新登录"
                }
            }
        ]
    }
]
"""
    config = {"configurable":{"thread_id":"1"}}
    res = ApiBaseCaseGeneratorWorkflow().create_basecase_workflow().stream({"api_doc":api_doc,"precoditions":[]},
                            config=config,
                            stream_mode=["messages","custom"],
                            context={"project_name":"1","module_id":"1"}
                            )
    print("=========================")
    # for chunk in res:
    #     print(chunk)
    for chunk in res:
        if chunk[0] == "custom":
            print(chunk[1])
        elif chunk[0] == "messages":
            print(chunk[1][0].content,end="",flush=True)