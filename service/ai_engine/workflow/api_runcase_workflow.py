"""
再次封装一个工作流，负责下面这种格式的用例转换为可以直接执行的接口用例 ————> 预执行验证用例的可执行性
{
    'name': '登录-正常请求',
    'steps': ['请求获取登录验证码', '登录', '发送 POST 请求到 /member/public/login，请求体 Content-Type 为 application/x-www-form-urlencoded，包含正确的手机号（keywords）和密码（password）'],
    'expected': ['HTTP 状态码: 200', '响应体 status 字段: 200', "响应体 description 字段: '登录成功'"],
    'dependencies': ['获取登录验证码']
}
核心工作流程设计：
    1、 基于基础的用例，生成可执行的用例
        —— 输出的数据内容：
            -  基础用例
            -  涉及到的接口的接口文档（主接口，前置依赖数据提取相关的接口）
            -  涉及到文件上传的接口，还需要提供可用的文件列表
            -  前后置脚本执行（自定义的工具函数：生成随机数，对数据加密。。。）
            -  提供测试环境中预置的测试数据
    2、对生成的用例进行预执行，验证用例的可执行性
    3、输出可执行的用例，并进行标记。

"""
from langchain_core.output_parsers import JsonOutputParser
from langgraph.config import get_stream_writer
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field
from typing import TypedDict, Optional, List
from langgraph.checkpoint.memory import InMemorySaver

from service.ai_engine.prompts.api_workflow.api_runcase_generator_prompt import api_runcase_generator_prompt, output_format
from service.ai_engine.prompts.api_workflow.api_runcase_regenerator_prompt import api_runcase_regenerator_prompt
from service.core.settings import llm, BASE_DIR, MAX_GENERATOR_COUNT
from service.ai_generation.common import build_default_additional_info
from service.ai_engine.shared.get_script_function_list import get_module_functions
from service.ai_engine.shared.get_test_file_list import inspect_env_data
from service.ai_engine.parsers.api_document_ai_parser import safe_structure_parser, _convert_to_serializable
from service.ai_engine.shared.messages import msg, lang_from_overlay

from ApiEngine.core import TestRunner

checkpointer=InMemorySaver()

class APIState(TypedDict):
    """定义工作流的数据状态"""
    project: str  # 所属项目
    environment_id: int  # 测试环境 ID，>0 时从平台加载 test_env_data
    base_case: dict  # 基础用例
    api_doc: str  # 主接口的文档
    precoditions_api_doc: list  # 接口前置依赖
    test_env_data: dict  # 全局环境数据（含可定义函数、测试数据、数据库环境配置等） -- 传入数据格式（兼容接口执行引擎）
    test_data: dict # 测试数据
    additional_info: str  # 额外信息
    test_files: dict  # 测试文件集合
    function_list: list  # 前后置脚本中可以引用的工具函数列表
    api_case: dict  # 生成的可执行的用例
    api_case_run_result: dict  # 执行用例的结果
    exec_result: dict  # 执行结果（传递给 output_runcase 输出）
    review_status: str # 生成的用例是否可执行
    generator_count: int # 生成用例的次数
    skip_execution: bool  # 为 True 时跳过执行阶段，仅做结构化
    language_overlay: str  # 语言覆盖指令


def _resolve_test_env_data(state: APIState) -> dict:
    test_env_data = state.get("test_env_data")
    if test_env_data:
        return test_env_data
    environment_id = state.get("environment_id") or 0
    if environment_id:
        from service.test_execution.env_loader import load_test_env_data_plain

        return load_test_env_data_plain(environment_id)
    # 无环境时：如果仅做结构化（skip_execution=True），返回空数据允许 LLM 继续执行
    if state.get("skip_execution"):
        return {
            "base_url": "",
            "headers": {},
            "envs": {},
            "global_func": "",
            "db": [],
        }
    raise RuntimeError(
        "预执行需要有效的 environment_id 或 test_env_data；请在 confirm 时指定测试环境"
    )


def _hardcoded_test_env_data() -> dict:
    """仅用于 workflow __main__ 本地演示，生产路径不应调用。"""
    from service.core.settings import AI_DEMO_GLOBAL_FUNC_PATH

    file_path = str(AI_DEMO_GLOBAL_FUNC_PATH)
    return {
        "base_url": "http://121.43.169.97:8081",
        "headers": {"Content-Type": "application/json"},
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
                    "password": "P2P_student_2023",
                },
            }
        ],
    }


class APIruncaseModel(BaseModel):
    """定义可执行的接口测试用例数据模型"""
    title: str = Field(description="用例名称",max_length=100)  # 用例名称
    description: Optional[str] = Field(None,description="用例描述")  # 用例描述
    project: str = Field(description="所属项目") # 所属项目
    module: str = Field(description="用例所属模块")  # 用例所属模块
    interface: dict = Field(description="接口信息") # 接口信息
    headers: dict = Field(description="请求头信息") # 请求头信息
    request: dict = Field(description="请求体信息") # 请求体信息
    preconditions: list = Field(description="前置依赖接口") # 前置依赖接口
    setup_script: str = Field(description="前置python脚本字符串") # 前置python脚本
    teardown_script: str = Field(description="后置python脚本字符串") # 后置python脚本
    extract: list = Field(description="提取变量") # 提取变量
    assertions: list = Field(description="断言") # 断言

class APIRuncaseGeneratorWorkflow:
    """定义可运行的接口用例生成工作流"""

    # 1、获取测试环境数据(测试数据、工具函数、测试文件、前置依赖接口)
    def get_test_env_data(self,state:APIState):
        """获取测试环境数据(测试数据、工具函数、测试文件、前置依赖接口)"""
        writer = get_stream_writer()
        _lang = lang_from_overlay(state.get("language_overlay", ""))
        writer(msg("run_wf.node1_start", _lang))
        test_env_data = _resolve_test_env_data(state)
        # 1、获取测试数据
        test_data = test_env_data.get("envs")
        # 2、获取自定义的工具函数
        function_list = get_module_functions(test_env_data.get("global_func"))
        # 3、获取测试文件
        test_files = inspect_env_data(test_env_data)
        # 4、获取前置依赖接口
        precoditions_api_doc = state.get("precoditions_api_doc") or []
        writer(msg("run_wf.node1_end", _lang))
        # 5、返回测试环境数据
        return {
            "test_data": test_data,
            "function_list": function_list,
            "test_files": test_files,
            "precoditions_api_doc": precoditions_api_doc
        }

    # 2、生成可运行的api结构化测试用例
    def structure_runcase_generator(self, state: APIState):
        """结构化接口用例生成"""
        # 1、获取API接口文档和对应的依赖接口
        writer = get_stream_writer()
        _lang = lang_from_overlay(state.get("language_overlay", ""))
        writer(msg("run_wf.node2_start", _lang))
        # 2、调用AI模型生成基础的测试用例
        parser = JsonOutputParser(pydantic_schema=APIruncaseModel)
        resp = safe_structure_parser(api_runcase_generator_prompt,llm,parser,
                                     {'output_format':output_format,
                                     'base_case':state.get("base_case"),
                                     'api_doc':state.get("api_doc"),
                                     'precoditions_api_doc':state.get("precoditions_api_doc"),
                                     'test_data':state.get("test_data"),
                                     'test_files':state.get("test_files"),
                                     'function_list':state.get("function_list"),
                                     'additional_info': state.get("additional_info"),
                                     'language_overlay': state.get("language_overlay", ""),
                                      })
        # ★ 归一化：确保 api_case 始终为单个 dict
        if isinstance(resp, list):
            if len(resp) > 0:
                resp = resp[0]
            else:
                resp = None
        elif not isinstance(resp, dict):
            resp = None
        writer(msg("run_wf.node2_done", _lang))
        # ★ 根据接口文档修正 AI 生成的前置步骤 Content-Type / body 字段
        if isinstance(resp, dict):
            _pre_list = resp.get("preconditions")
            _precoditions_docs = state.get("precoditions_api_doc") or []
            if _pre_list and isinstance(_pre_list, list):
                from service.api_test.shared.payload_builder import normalize_preconditions
                writer(f"★ normalize: AI 生成 {len(_pre_list)} 个前置步骤, 接口文档 {len(_precoditions_docs)} 个")
                resp["preconditions"] = normalize_preconditions(
                    _pre_list, _precoditions_docs,
                )
            else:
                writer(f"★ normalize: 无前置步骤需要修正 (preconditions={type(_pre_list).__name__})")
        # 3、返回基础的测试用例
        return {"api_case": resp}

    # 3、预执行生成的结构化接口用例
    def api_case_run(self, state: APIState):
        """执行生成的结构化接口用例"""
        writer = get_stream_writer()
        _lang = lang_from_overlay(state.get("language_overlay", ""))
        writer(msg("run_wf.node3_start", _lang))
        api_case_raw  = state.get("api_case")
        test_env_data = _resolve_test_env_data(state)
        result = {}
        # 1、将生成的可执行用例格式（List），转换成测试引擎可执行的用例格式（dict)
        runner_api_case = None
        if isinstance(api_case_raw, list) and len(api_case_raw) > 0:
            runner_api_case = api_case_raw[0]
        elif isinstance(api_case_raw, dict):
            runner_api_case = api_case_raw
        # 2、调用接口执行引擎执行用例
        if runner_api_case:
            try:
                # 注意：需要深拷贝一份，避免影响原数据（因为 execute_cases 会 pop db）
                import copy
                env_copy = copy.deepcopy(test_env_data)
                runner = TestRunner(env_copy)
                result = runner.execute_cases(runner_api_case)
                # ★★★ 关键修复：转换执行结果为可序列化格式 ★★★
                result = _convert_to_serializable(result)
            except Exception as e:
                err_msg = str(e)
                result = {"status": "error", "message": err_msg}
                writer(f"执行异常详情：{err_msg}")
        else:
            result = {"status": "error", "message": "无可执行的用例数据"}
        # 3、判断用例是否可执行，并返回用例是否可执行的结果（包括：用例执行结果，是否可执行，已执行次数）
        # 执行次数
        generator_count = state.get("generator_count", 0) + 1
        # 是否可执行
        review_status = result.get("state") or result.get("status", "init")
        writer(f"执行的结果为：{result},可执行状态：{review_status},已执行次数：{generator_count}")
        # 2、返回执行结果
        writer(msg("run_wf.node3_done", lang_from_overlay(state.get("language_overlay", ""))))
        return {"api_case_run_result": result,"review_status": review_status,"generator_count": generator_count}

    # 4、重新生成可执行的结构化接口用例
    def re_structure_runcase_generator(self, state: APIState):
        """重新生成可执行的结构化接口用例"""
        # 1、获取API接口文档和对应的依赖接口
        writer = get_stream_writer()
        writer(msg("run_wf.node4_start", lang_from_overlay(state.get("language_overlay", ""))))
        # 2、调用AI模型生成基础的测试用例
        parser = JsonOutputParser(pydantic_schema=APIruncaseModel)
        resp = safe_structure_parser(api_runcase_regenerator_prompt,llm,parser,
                                     {'output_format':output_format,
                                     'base_case':state.get("base_case"),
                                     'api_doc':state.get("api_doc"),
                                     'precoditions_api_doc':state.get("precoditions_api_doc"),
                                     'test_data':state.get("test_data"),
                                     'test_files':state.get("test_files"),
                                     'function_list':state.get("function_list"),
                                     'additional_info': state.get("additional_info"),
                                      "api_case_run_result":state.get("api_case_run_result"),
                                      "api_case":state.get("api_case"),
                                      'language_overlay': state.get("language_overlay", ""),
                                      })
        writer(msg("run_wf.node4_done", lang_from_overlay(state.get("language_overlay", ""))))
        # ★ 根据接口文档修正 AI 生成的前置步骤 Content-Type / body 字段
        if isinstance(resp, dict):
            _pre_list = resp.get("preconditions")
            _precoditions_docs = state.get("precoditions_api_doc") or []
            if _pre_list and isinstance(_pre_list, list):
                from service.api_test.shared.payload_builder import normalize_preconditions
                writer(f"★ normalize(重试): AI 生成 {len(_pre_list)} 个前置步骤, 接口文档 {len(_precoditions_docs)} 个")
                resp["preconditions"] = normalize_preconditions(
                    _pre_list, _precoditions_docs,
                )
            else:
                writer(f"★ normalize(重试): 无前置步骤需要修正")
        # 3、返回基础的测试用例
        return {"api_case": resp}

    # 5、输出生成的可执行的结构化接口用例
    def output_runcase(self, state: APIState):
        """输出生成的接口用例"""
        # 1、获取生成的接口用例
        writer = get_stream_writer()
        writer(msg("run_wf.node5_start", lang_from_overlay(state.get("language_overlay", ""))))
        api_case = state.get("api_case")
        review_status = state.get("review_status")
        exec_result = state.get("api_case_run_result") or {}
        # skip_execution 模式下，没有执行结果，review_status 设为 init
        if state.get("skip_execution"):
            review_status = "init"
            exec_result = {}
        # 2、返回用例结果
        api_case.setdefault("review_status", review_status)
        writer(f"最终生成的接口用例为：{api_case},可执行状态：{review_status}")
        writer(msg("run_wf.node5_done", lang_from_overlay(state.get("language_overlay", ""))))
        return {
            "api_case": _convert_to_serializable(api_case),
            "review_status": review_status,
            "exec_result": _convert_to_serializable(exec_result),
        }

    # 5、检查生成次数（默认最大重试次数为3次)
    def check_generator_count(self,state:APIState):
        """检查生成次数"""
        generator_count = state.get("generator_count")
        review_status = state.get("review_status")
        if generator_count < MAX_GENERATOR_COUNT and review_status not in ("success", "fail"):
            return "re_structure_runcase_generator"
        else:
            return "output_runcase"

    def route_after_structure(self, state: APIState):
        """结构化完成后路由：skip_execution=True 时直接输出，否则进入执行阶段"""
        if state.get("skip_execution"):
            return "output_runcase"
        return "api_case_run"

    def create_runcase_workflow(self):
        """创建可运行的接口用例生成工作流"""
        # 1、创建工作流节点
        builder = StateGraph(APIState)
        builder.add_node("get_test_env_data",self.get_test_env_data)
        builder.add_node("structure_runcase_generator",self.structure_runcase_generator)
        builder.add_node("api_case_run",self.api_case_run)
        builder.add_node("re_structure_runcase_generator",self.re_structure_runcase_generator)
        builder.add_node("output_runcase",self.output_runcase)
        builder.add_node("check_generator_count",self.check_generator_count)
        # 2、流程编排
        builder.add_edge(START,"get_test_env_data")
        builder.add_edge("get_test_env_data","structure_runcase_generator")
        builder.add_conditional_edges("structure_runcase_generator", self.route_after_structure, {"api_case_run": "api_case_run", "output_runcase": "output_runcase"})
        builder.add_conditional_edges("api_case_run",self.check_generator_count)
        builder.add_edge("re_structure_runcase_generator","api_case_run")
        builder.add_edge("output_runcase",END)
        # 3、返回工作流
        return builder.compile(checkpointer=checkpointer)



if __name__ == '__main__':
    import sys

    from service.core import settings as core_config

    if not core_config.AITESTPLATFORM_ALLOW_WORKFLOW_MAIN:
        print("Set AITESTPLATFORM_ALLOW_WORKFLOW_MAIN=1 to run this workflow demo")
        sys.exit(0)
    base_case = [
  {
    "name": "验证账号被锁定后立即重试登录",
    "steps": [
      "调用已有用例'密码错误第3次后被锁定'，使指定账号被锁定",
      "立即再次发送POST请求到接口路径 /member/public/login",
      "设置请求头 Content-Type: application/x-www-form-urlencoded",
      "在请求体中填入被锁定账号的手机号（keywords）和正确的密码（password）"
    ],
    "expected": [
      "HTTP状态码为200",
      "响应体为JSON格式",
      "status字段值为100",
      "description字段仍显示锁定提示信息（表明锁定有效期内无法登录）"
    ],
    "dependencies": [
        "密码错误第1次后,提示达到3次将锁定账户",
        "密码错误第2次后,提示达到3次将锁定账户",
        "密码错误第3次后被锁定"
    ]
  }]
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
    additional_info = build_default_additional_info()
    # 全局环境数据
    file_path = str(BASE_DIR / "data" / "test_data" / "Tools.py")
    test_env_data = {
        "base_url": "http://121.43.169.97:8081",
        "headers": {
            "Content-Type": "application/json"
        },
        # 环境变量
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
    config = {"configurable": {"thread_id": "1"}}
    res = APIRuncaseGeneratorWorkflow().create_runcase_workflow().stream({"base_case": base_case,"api_doc":api_doc,"additional_info":additional_info,"test_env_data":test_env_data,"generator_count":0},
                                                                         config=config,
                                                                         stream_mode=["messages", "custom"],
                                                                         )
    for chunk in res:
        if chunk[0] == "messages":
            print(chunk[1][0].content, end="", flush=True)
        elif chunk[0] == "custom":
            # writer() 内容每条独立一行，自动换行
            print(chunk[1], end="\n", flush=True)