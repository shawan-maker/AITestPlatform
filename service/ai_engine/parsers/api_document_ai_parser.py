"""
通过AI解析接口文档
"""
import json
import logging
import re
from typing import List

from langchain_core.output_parsers import JsonOutputParser

from service.ai_engine.prompts.parser.api_parser_prompt import api_parser_prompt
from service.core.settings import llm
from service.ai_engine.parsers.api_document_models import (
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
      3. 修复常见 LLM JSON 格式问题（尾逗号、单引号等）后重试
      4. 提取 [ ... ] 数组片段
      5. 用 raw_decode 逐个提取连续 JSON 对象（处理 {...}{...} 拼接）
      6. 全部失败返回 fallback
    """
    if not raw_text or not isinstance(raw_text, str):
        logging.error(f"_safe_json_parse: 输入为空或非字符串, type={type(raw_text).__name__}")
        return fallback

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

    # ━━━ 策略3：修复常见 LLM JSON 格式问题 ━━━
    fixed = cleaned if cleaned != text else text
    # 去除 JSON 中的注释（// 和 /* */）
    fixed = re.sub(r'//[^\n]*', '', fixed)
    fixed = re.sub(r'/\*.*?\*/', '', fixed, flags=re.DOTALL)
    # 去除尾逗号（,] 和 ,}）
    fixed = re.sub(r',\s*([\]}])', r'\1', fixed)
    # 将单引号替换为双引号（仅在 JSON 键值对位置）
    if "'" in fixed and '"' not in fixed:
        fixed = fixed.replace("'", '"')
    if fixed != (cleaned if cleaned != text else text):
        try:
            result = json.loads(fixed)
            if isinstance(result, (dict, list)):
                return result
        except (json.JSONDecodeError, TypeError):
            pass

    # ━━━ 策略4：提取第一个 [...] 数组片段 ━━━
    search_text = fixed if fixed != text else (cleaned if cleaned != text else text)
    match = re.search(r'\[.*\]', search_text, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group(0))
            if isinstance(result, list):
                return result
        except (json.JSONDecodeError, TypeError):
            # 尝试修复后再解析
            arr_text = match.group(0)
            arr_text = re.sub(r',\s*([\]}])', r'\1', arr_text)
            try:
                result = json.loads(arr_text)
                if isinstance(result, list):
                    return result
            except (json.JSONDecodeError, TypeError):
                pass

    # ━━━ 策略5：处理多个 JSON 对象拼接的情况 {...}{...} ━━━
    # 使用 json.decoder.JSONDecoder 的 raw_decode 逐个提取
    parse_target = search_text
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
    logging.error(f"_safe_json_parse: 所有策略均失败, 文本长度={len(text)}, 前300字: {text[:300]}")
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
            logging.warning(f"AI 返回类型异常: {type(resp).__name__}, 值={resp!r:.200}")
            resp = None
        else:
            count = len(resp) if isinstance(resp, list) else 1
            logging.info(f"AI 结构化解析成功: type={type(resp).__name__}, count={count}")
    except Exception as e:
        # JsonOutputParser 解析失败时，回退到手动安全解析
        logging.warning(f"【JSON解析异常】 {e}，启用容错解析")
        raw_chain = prompt | llm
        raw_resp = raw_chain.invoke(input_data)
        raw_content = raw_resp.content if hasattr(raw_resp, 'content') else str(raw_resp)
        logging.info(f"LLM 原始响应长度: {len(raw_content)} 字符, 前500字: {raw_content[:500]}")
        # 记录 LLM 响应元数据（帮助诊断空响应问题）
        if hasattr(raw_resp, 'response_metadata'):
            logging.info(f"LLM 响应元数据: {raw_resp.response_metadata}")
        if not raw_content:
            logging.error(f"LLM 返回空内容! response_metadata={getattr(raw_resp, 'response_metadata', None)}, "
                         f"additional_kwargs={getattr(raw_resp, 'additional_kwargs', None)}")
        resp = _safe_json_parse(raw_content)
        if resp is not None:
            count = len(resp) if isinstance(resp, list) else 1
            logging.info(f"容错解析成功: type={type(resp).__name__}, count={count}")
        else:
            # 再重试一次，用更简短的提示要求 LLM 只输出 JSON
            logging.warning("容错解析失败，进行最后一次重试")
            try:
                from langchain_core.prompts import PromptTemplate
                # 使用原始 prompt 的 input_variables 构建重试提示
                retry_template = "请重新输出，确保只输出纯JSON数组，不要包含任何其他文字、注释或markdown标记。请直接输出JSON："
                # 复用原始 prompt 的模板变量，在末尾追加重试指令
                original_template = prompt.template if hasattr(prompt, 'template') else str(prompt)
                retry_full_template = original_template + "\n\n[重要] " + retry_template
                retry_prompt = PromptTemplate(
                    input_variables=prompt.input_variables if hasattr(prompt, 'input_variables') else [],
                    template=retry_full_template,
                )
                retry_chain = retry_prompt | llm
                retry_resp = retry_chain.invoke(input_data)
                retry_content = retry_resp.content if hasattr(retry_resp, 'content') else str(retry_resp)
                logging.info(f"重试LLM响应长度: {len(retry_content)} 字符, 前500字: {retry_content[:500]}")
                if not retry_content:
                    logging.error(f"重试LLM也返回空内容! metadata={getattr(retry_resp, 'response_metadata', None)}")
                resp = _safe_json_parse(retry_content)
                if resp is not None:
                    count = len(resp) if isinstance(resp, list) else 1
                    logging.info(f"重试解析成功: type={type(resp).__name__}, count={count}")
                else:
                    logging.error("重试解析也失败，返回 None")
            except Exception as retry_exc:
                logging.error(f"重试过程异常: {retry_exc}，返回 None")

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
    def api_parser(self, api_document: str, llm_instance=None):
        """
        :param api_document: 接口文档
        :param llm_instance: 可选的自定义 LLM 实例（用于覆盖全局 llm）
        :return:
        """
        logging.info("【开始执行节点】 1、解析接口文档为特定json格式")
        # 定义一个结果提取器
        parser = JsonOutputParser(pydantic_object=List[APIDocumentParserModel])
        # 使用传入的 LLM 实例或全局 llm
        actual_llm = llm_instance if llm_instance is not None else llm
        # 调用结构化解析
        resp = safe_structure_parser(api_parser_prompt, actual_llm, parser, {"input_text": api_document})
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