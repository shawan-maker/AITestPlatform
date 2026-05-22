"""
  1、根据接口文档生成基础的接口用例
  2、根据基础的接口用例，生成可执行的结构化接口用例
  3、保存结构化接口用例到数据库
"""
import functools
import json
import operator
import sys
from concurrent.futures import ThreadPoolExecutor

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.types import Send
from pydantic import BaseModel, Field
from typing import TypedDict, Optional, List, Annotated
from langgraph.checkpoint.memory import InMemorySaver

from config.settings import BASE_DIR, MAX_BATCH_SIZE
from utils.logger.logger import _ThreadSafeStdout
from workflow.api_basecase_workflow import ApiBaseCaseGeneratorWorkflow, StateNode
from workflow.api_runcase_workflow import APIRuncaseGeneratorWorkflow, APIState
checkpointer=InMemorySaver()


class mainState(TypedDict):
    api_doc: str  # API接口文档
    project_name: str  # 项目名称
    module_name: str  # 模块名称
    precoditions: list[str]  # 前置执行依赖接口的调用顺序
    base_cases: List  # 生成的测试用例（所有用例 - 列表）
    base_case: dict # 生成的基础测试用例（单个用例 - 预执行）
    test_env_data: dict # 全局环境数据（含可定义函数、测试数据、数据库环境配置等）
    additional_info: dict # 额外信息（含项目名称、模块名称、注意事项等）
    generator_count:int  # 重新生成结构化测试用例的次数
    api_run_cases: Annotated[List,operator.add]  # 最终生成的可运行用例

# 主工作流(使用多线程并发 生成可执行的接口测试用例)
class APICaseGeneratorMainWorkflow:
    """
    1、根据接口文档生成基础的接口用例
    2、根据基础的接口用例，生成可执行结构化接口用例
    3、保存结构化接口用例到数据库
    """
    # 1、根据接口文档生成基础的接口用例
    def generator_api_basecase(self,state:mainState,config: RunnableConfig):
        writer = get_stream_writer()
        writer("【开始执行主流程节点】 1、生成api基础测试用例：")
        workflow = ApiBaseCaseGeneratorWorkflow().create_basecase_workflow()
        basecase_state:StateNode = workflow.invoke(
                                    {"api_doc": state.get("api_doc"), "precoditions": state.get("precoditions")},
                                   config=config
                                   )
        writer("【执行主流程节点完成】 1、生成api基础测试用例：")
        return {"base_cases":basecase_state.get("api_cases")}

    # 2、根据基础的接口用例，生成可执行结构化接口用例
    def generator_api_structure_runcase(self,state:mainState,config: RunnableConfig):
        """
        并发执行的节点 — 使用多线程并发 生成可执行的接口测试用例
        使用 _ThreadSafeStdout 替换 sys.stdout 实现线程级输出隔离（含 per-task buffer 隔离）
        """
        import io

        writer = get_stream_writer()
        writer("【开始执行主流程节点】 2、生成可执行结构化接口用例：")

        # 创建线程安全的 stdout 替换实例
        _safe_stdout = _ThreadSafeStdout(sys.stdout)
        # 全局替换 stdout（所有线程的 print/logging 都会走这里）
        sys.stdout = _safe_stdout

        # 用于收集每个任务的输出 {future: StringIO}
        task_outputs = {}

        try:
            # 创建线程池(设置线程池的最大工作线程数为MAX_BATCH_SIZE)
            with ThreadPoolExecutor(max_workers=MAX_BATCH_SIZE) as executor:
                future_list = []
                # 提交任务到线程池
                for idx, base_case in enumerate(state.get("base_cases", [])):
                    # 为每个任务创建独立的子工作流
                    workflow = APIRuncaseGeneratorWorkflow().create_runcase_workflow()

                    # ★ 为每个任务创建独立的 buffer
                    buf = io.StringIO()

                    # ★ 构造 invoke 参数（state + config）
                    invoke_kwargs = {
                        "input": {
                            "base_case": base_case,
                            "api_doc": state.get("api_doc"),
                            "additional_info": state.get("additional_info"),
                            "test_env_data": state.get("test_env_data"),
                            "generator_count": state.get("generator_count",0)
                        },
                        "config": config,
                    }

                    # ★ 用 wrapper 包裹：先设 buffer → 执行 → 记录 buffer
                    def _run_with_buffer(wf, kwargs, buffer, task_idx):
                        _safe_stdout.set_buffer(buffer)  # 关键：绑定当前线程的 buffer
                        try:
                            return wf.invoke(**kwargs)
                        finally:
                            pass  # buffer 保持，直到主线程读取

                    future = executor.submit(_run_with_buffer, workflow, invoke_kwargs, buf, idx)
                    task_outputs[future] = buf  # 记录 buffer 以便后续读取
                    # 将返回的Future对象添加到列表中
                    future_list.append(future)

                # 等待线程池中的所有任务执行完毕，获取每个任务的返回结果
                result = []
                for future in future_list:
                    api_case = future.result().get("api_case")
                    result.append(api_case)

                    # ★ 按顺序输出每个任务的完整日志（有序!）
                    buf = task_outputs[future]
                    task_log = buf.getvalue()
                    if task_log.strip():
                        print(f"\n{'='*20} 任务 {future_list.index(future)+1}/{len(future_list)} 输出 {'='*20}")
                        print(task_log, end="")
        finally:
            # ★ 恢复原始 stdout（确保无论成功/异常都恢复）
            sys.stdout = _safe_stdout._original

        writer("【执行主流程节点完成】 2、生成可执行结构化接口用例")
        return {"api_run_cases": result}

    # 3、保存结构化接口用例到数据库
    def save_api_runcase_to_db(self,state:mainState):
        writer = get_stream_writer()
        writer("【开始执行主流程节点】 4、保存结构化接口用例到数据库：")
        # 保存结构化接口用例到数据库
        # 将结构化接口用例写入到文件 test_data下的api_run_cases.json 中
        file_path = BASE_DIR + "/test_data/api_run_cases.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state.get("api_run_cases"), f, ensure_ascii=False, indent=4)
        writer(f"一共生成 {len(state.get('api_run_cases'))} 个结构化接口用例，并保存到 {file_path} 中")
        writer("【执行主流程节点完成】 4、保存结构化接口用例到数据库：")
        return {}

    # 6、创建主工作流
    def create_main_workflow(self):
        # 1、添加节点
        builder = StateGraph(mainState)
        builder.add_node("generator_api_basecase",self.generator_api_basecase)
        builder.add_node("generator_api_structure_runcase",self.generator_api_structure_runcase)
        builder.add_node("save_api_runcase_to_db",self.save_api_runcase_to_db)
        # 2、对执行节点进行编排
        builder.add_edge(START, "generator_api_basecase")
        builder.add_edge("generator_api_basecase", "generator_api_structure_runcase")
        builder.add_edge("generator_api_structure_runcase", "save_api_runcase_to_db")
        builder.add_edge("save_api_runcase_to_db", END)
        # 3、返回工作流
        return builder.compile(checkpointer=checkpointer)

# 主工作流(使用 Send并发 生成可执行的接口测试用例)
class APICaseGeneratorMainWorkflow2:
    """
    1、根据接口文档生成基础的接口用例
    2、根据基础的接口用例，生成可执行结构化接口用例
    3、保存结构化接口用例到数据库
    """
    # 1、根据接口文档生成基础的接口用例
    def generator_api_basecase(self,state:mainState):
        writer = get_stream_writer()
        writer("【开始执行主流程节点】 1、生成api基础测试用例：")
        workflow = ApiBaseCaseGeneratorWorkflow().create_basecase_workflow()
        basecase_state:StateNode = workflow.invoke(
                                    {"api_doc": state.get("api_doc"), "precoditions": state.get("precoditions")},
                                   config=config
                                   )
        writer("【执行主流程节点完成】 1、生成api基础测试用例：")
        return {"base_cases":basecase_state.get("api_cases")}

    # 2、根据基础的接口用例，生成可执行结构化接口用例
    def generator_api_structure_runcase(self,state:mainState):
        """
        并发执行的节点 — 每个 Send 任务独立运行在此节点中
        通过线程本地存储区分不同任务的日志
        """
        writer = get_stream_writer()
        writer("【开始执行主流程节点】 2、生成可执行结构化接口用例：")
        workflow = APIRuncaseGeneratorWorkflow().create_runcase_workflow()
        runcase_state: APIState = workflow.invoke(
                                     {"base_case": state.get("base_case"),
                                      "api_doc": state.get("api_doc"),
                                      "additional_info": state.get("additional_info"),
                                      "test_env_data": state.get("test_env_data"),
                                      "generator_count": state.get("generator_count")
                                      },
                                     config=config
                                 )
        writer("【执行主流程节点完成】 2、生成可执行结构化接口用例")
        api_case = runcase_state.get("api_case")
        return {"api_run_cases": [api_case]}

    # 3、对所有基础用例进行任务拆分，分别进行结构化用例生成
    def api_case_generation_task_split(self,state:mainState):
        """发送并发任务
╔══════════════════════════════════════════════════════════╗
║   方案1、使用Send，则会同时执行所有任务，可能触发AGI限流          ║
║   方案2：Send + 分批次循环 在当前 LangGraph 中【无法实现】      ║
║                                                          ║
║   原因不是代码写法问题，而是 LangGraph 图结构的                 ║
║   【根本性设计限制】：                                       ║
║                                                          ║
║   • 条件边函数能返回 Send → 但不能成为路由目标                 ║
║   • 普通节点能成为路由目标 → 但不能返回 Send                   ║
║   • 两者互斥，无法同时具备                                   ║
║                                                          ║
║   唯一可行方案3：                                           ║
║   ────────────────────                                   ║
║   【单节点内 ThreadPoolExecutor 并发】                      ║
║   用 Python 线程池替代 LangGraph Send 做 fan-out            ║
║   用条件边(str→节点)实现循环                                 ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
        """

        # BATCH_SIZE = MAX_BATCH_SIZE
        # all_cases = state.get("base_cases", [])
        # # 1、计算当前批次
        # # ★ 唯一需要的：已处理了多少条 → 自然知道该处理第几批了
        # processed = len(state.get("api_run_cases", []))
        # batch = all_cases[processed: processed + BATCH_SIZE]
        # if not batch:
        #     # 所有批次已处理完毕
        #     return [END]
        # 2、分批次创建并发任务
        task_list = []
        # for base_case in batch:
        for base_case in state.get("base_cases", []):
            task_list.append(
                Send('generator_api_structure_runcase',{
                    "base_case": base_case,
                    "api_doc": state.get("api_doc"),
                    "additional_info": state.get("additional_info"),
                    "test_env_data": state.get("test_env_data"),
                    "generator_count": 0
                })
            )
        return task_list

    # 4、保存结构化接口用例到数据库
    def save_api_runcase_to_db(self,state:mainState):
        writer = get_stream_writer()
        writer("【开始执行主流程节点】 4、保存结构化接口用例到数据库：")
        # 保存结构化接口用例到数据库
        writer("【执行主流程节点完成】 4、保存结构化接口用例到数据库：")
        return {"api_run_cases": state.get("api_run_cases")}

    # # 5、检查是否还有剩余批次
    # def check_remaining_batches(self, state: mainState):
    #     """检查是否还有剩余批次"""
    #     all_cases = state.get("base_cases", [])
    #     processed_count = len(state.get("api_run_cases", []))
    #
    #     if processed_count < len(all_cases):
    #         return "api_case_generation_task_split"  # 继续下一批
    #     else:
    #         return "save_api_runcase_to_db"  # 全部完成

    # 6、创建主工作流
    def create_main_workflow(self):
        # 1、添加节点
        builder = StateGraph(mainState)
        builder.add_node("generator_api_basecase",self.generator_api_basecase)
        builder.add_node("generator_api_structure_runcase",self.generator_api_structure_runcase)
        builder.add_node("save_api_runcase_to_db",self.save_api_runcase_to_db)
        # 2、对执行节点进行编排
        builder.add_edge(START, "generator_api_basecase")
        builder.add_conditional_edges("generator_api_basecase", self.api_case_generation_task_split,["generator_api_structure_runcase"])
        builder.add_edge("generator_api_structure_runcase", "save_api_runcase_to_db")
        builder.add_edge("save_api_runcase_to_db", END)
        # 3、返回工作流
        return builder.compile(checkpointer=checkpointer)

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
    additional_info = {
        "project": "p2p金融项目",
        "module": "登录模块",
        "notice": "对于不能重复使用的数据，请使用工具随机生成数据",
    }
    # 全局环境数据
    file_path = BASE_DIR + r"\test_data\Tools.py"
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
    res = APICaseGeneratorMainWorkflow().create_main_workflow().stream({"api_doc":api_doc,"precoditions":[],"additional_info":additional_info,"test_env_data":test_env_data},
                                                                         config=config,
                                                                         stream_mode=["messages", "custom"],
                                                                         )
    for chunk in res:
        if chunk[0] == "messages":
            print(chunk[1][0].content, end="", flush=True)
        elif chunk[0] == "custom":
            # writer() 内容每条独立一行，自动换行
            print(chunk[1], end="\n", flush=True)