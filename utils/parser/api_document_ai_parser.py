"""
通过AI解析接口文档
"""
import json
import logging
import re
from typing import List

from langchain_core.output_parsers import JsonOutputParser

from config.prompts.parser.api_parser_prompt import api_parser_prompt
from config.settings import llm
from utils.parser.api_document_models import (
    APIDocumentParserModel,
    BodyField,
    Parameter,
    RequestBody,
    Response,
)


def _convert_to_serializable(obj):
    """
    递归转换对象为 JSON/msgpack 可序列化的格式
    主要解决：CaseInsensitiveDict, datetime, 自定义对象等无法序列化的问题
    """
    from collections.abc import Mapping
    from datetime import datetime, date

    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Mapping):
        # 将 CaseInsensitiveDict, OrderedDict 等统一转为普通 dict
        return {k: _convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [_convert_to_serializable(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        # 尝试将自定义对象转为 dict
        return {k: _convert_to_serializable(v) for k, v in obj.__dict__.items()
                if not k.startswith("_")}
    else:
        # 兜底：转为字符串
        return str(obj)


def _safe_json_parse(raw_text: str, fallback=None):
    """安全解析 LLM 返回的 JSON，带多级容错
    :param raw_text: LLM 返回的原始文本
    :param fallback: 全部策略失败时的兜底返回值（默认 None）
    :return: 解析结果 — 如果 LLM 输出单个对象则返回 dict，
             如果输出数组则返回 list，多对象拼接也返回 list，
             全部失败返回 fallback（默认 None）

    策略优先级：
      1. 直接 json.loads（保持原类型）
      2. 去除 markdown 代码块标记后重试
      3. 提取 [ ... ] 数组片段
      4. 用 raw_decode 逐个提取连续 JSON 对象（处理 {...}{...} 拼接）
      5. 全部失败返回 fallback
    """
    text = raw_text.strip()

    # ━━━ 策略1：直接 json.loads，保持原始类型 ━━━
    try:
        result = json.loads(text)
        if isinstance(result, (dict, list)):
            return result
    except (json.JSONDecodeError, TypeError):
        pass

    # ━━━ 策略2：去除 markdown ```json / ``` 标记后重试 ━━━
    cleaned = re.sub(r'^```(?:json)?\s*\n?', '', text)
    cleaned = re.sub(r'\n?```\s*$', '', cleaned).strip()
    if cleaned != text:  # 只有真正去除了标记才尝试
        try:
            result = json.loads(cleaned)
            if isinstance(result, (dict, list)):
                return result
        except (json.JSONDecodeError, TypeError):
            pass

    # ━━━ 策略3：提取第一个 [...] 数组片段 ━━━
    match = re.search(r'\[.*\]', cleaned or text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(0))
            if isinstance(result, list):
                return result
        except (json.JSONDecodeError, TypeError):
            pass

    # ━━━ 策略4：处理多个 JSON 对象拼接的情况 {...}{...} ━━━
    # 使用 json.decoder.JSONDecoder 的 raw_decode 逐个提取
    parse_target = cleaned if cleaned else text
    try:
        from json import JSONDecoder
        decoder = JSONDecoder()
        objects = []
        idx = 0
        while idx < len(parse_target):
            # 跳过空白字符
            while idx < len(parse_target) and parse_target[idx].isspace():
                idx += 1
            if idx >= len(parse_target):
                break
            try:
                obj, end_idx = decoder.raw_decode(parse_target, idx)
                objects.append(obj)
                idx = end_idx
            except (json.JSONDecodeError, ValueError):
                # 遇到无法解析的字符，跳过继续尝试
                idx += 1
        # 多个对象 → 返回列表；单个对象 → 返回字典本身
        if len(objects) == 1:
            return objects[0]
        elif len(objects) > 1:
            return objects
    except Exception:
        pass

    # ━━━ 兜底：全部失败 ━━━
    return fallback


def safe_structure_parser(prompt, llm, parser, input_data):
    """结构化解析，带多级容错

    :param prompt: 提示词模板
    :param llm: 大模型实例
    :param parser: 输出解析器（如 JsonOutputParser）
    :param param input_data: 模板输入变量
    :return: 解析结果 — 类型由 LLM 实际输出决定：
             单个对象 → dict，数组 → list，解析失败 → None
    """
    logging.info("【开始执行节点】 解析接口文档为特定json格式")

    # 创建一个调用链
    chain = prompt | llm | parser
    try:
        resp = chain.invoke(input_data)
        # ★ 移除强制列表包装：保持 JsonOutputParser 的原始返回类型
        # JsonOutputParser 通常返回 list（当 schema 是 List[] 时）或单个对象
        # 这里直接透传，不强制转换为 list
        if not isinstance(resp, (dict, list)):
            resp = None
    except Exception as e:
        # JsonOutputParser 解析失败时，回退到手动安全解析
        logging.info(f"【JSON解析异常】 generate_test_points: {e}，启用容错解析")
        raw_chain = prompt | llm
        raw_resp = raw_chain.invoke(input_data)
        resp = _safe_json_parse(raw_resp.content)

    logging.info(f"【执行节点完成】 解析接口文档为特定json格式，结果类型: {type(resp).__name__}")
    return resp


__all__ = [
    "APIDocumentParser",
    "APIDocumentParserModel",
    "BodyField",
    "Parameter",
    "RequestBody",
    "Response",
]


class APIDocumentParser:
    """
    通过AI解析接口文档，将接口文档转换为特定的结构化数据
    """
    def api_parser(self,api_document:str):
        """
        :param api_document: 接口文档
        :return:
        """
        logging.info("【开始执行节点】 1、解析接口文档为特定json格式")
        # 定义一个结果提取器
        parser = JsonOutputParser(pydantic_object=List[APIDocumentParserModel])
        # 调用结构化解析
        resp = safe_structure_parser(api_parser_prompt,llm,parser,{"input_text": api_document})
        return resp

if __name__ == '__main__':
    # res = AIParserApi.get_interface_uuid("POST", "/api/v1/order/submit")
    # print(res)
    data = """
        #### 登录

##### 基本信息

- `Path：/member/public/login`
- `Method:POST`
- 接口描述:

##### 请求参数

**headers**

| 参数名称     | 参数值                            | 是否必填 | 示例 | 备注 |
| ------------ | --------------------------------- | -------- | ---- | ---- |
| Content-Type | application/x-www-form-urlencoded |          |      |      |

**body**

| 参数名称 | 类型   | 是否必填 | 示例 | 备注   |
| -------- | ------ | -------- | ---- | ------ |
| keywords | string | 是       |      | 手机号 |
| password | string | 是       |      | 密码   |



##### 返回数据

- 响应状态码：200

- 状态码描述：

  - 200：登录成功，`{"status":200,"description":"登录成功"}`
  - 100：用户不存在，`{"status":100,"description":"用户不存在"}`
  - 100：密码不能为空，`{"status":100,"description":"密码不能为空"}`
  - 100：密码错误1次，`{"status":100,"description":"密码错误1次,达到3次将锁定账户"}`
  - 100：密码错误2次，`{"status":100,"description":"密码错误2次,达到3次将锁定账户"}`
  - 100：密码错误3次，`{"status":100,"description":"由于连续输入错误密码达到上限，账号已被锁定，请于1.0分钟后重新登录"}`



#### 是否登录

##### 基本信息

- `Path：/member/public/islogin`
- `Method:POST`
- 接口描述:判断是否登录

##### 返回数据

- 响应状态码：200

- 状态码描述：

  - 200：已登录，`{"status":200,"description":"OK"}`

  - 250：未登陆，`{"status":250,"description":"您未登陆！"}`
    """
    res = APIDocumentParser().api_parser(data)
    print(json.dumps(res, ensure_ascii=False, indent=4))