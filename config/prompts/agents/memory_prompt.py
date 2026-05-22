"""
memory_prompt.py
    长期记忆摘要提取 Prompt 模板
    用于 LLM 从每轮 Q&A 中提取结构化记忆摘要
"""

SUMMARY_EXTRACTION_PROMPT = """你是一个对话记忆提取助手。请从以下问答对中提取关键信息，输出 JSON 格式。

要求输出以下字段：
- action_type: 本次操作类型（如：需求检索、用例生成、接口检索等）
- target_module: 目标模块或功能点（如：登录、购物车等）
- result_summary: 本轮结果摘要（不超过50字）
- pending_items: 待办事项列表（如有）
- completed_items: 已完成事项列表（如有）
- history_summaries: 历史关键信息摘要列表（每条不超过30字）

用户问题: {query}
AI回答: {response}

请直接输出纯 JSON，不要包含其他说明文字。"""

# 长期记忆注入时的 System Prompt 模板
MEMORY_INJECTION_SYSTEM_TEMPLATE = """【历史对话记忆】
以下是你在之前的对话中的关键记录摘要，请基于这些上下文继续对话：

{memory_content}

请参考以上历史信息回应用户当前的问题。"""
