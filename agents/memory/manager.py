"""
manager.py —— 双记忆系统核心管理器
============================================
职责：
  1. 管理 LangGraph 的两套存储（checkpointer + memory_store）
  2. 控制长期记忆的读取（去重注入）和写入（LLM摘要+降级兜底）
  3. 为 Agent 对话提供标准化的消息准备流程

架构说明：
    Checkpointer (InMemorySaver)  →  单次会话内多轮交互的自动存储（短期记忆）
    InMemoryStore                 →  不同会话之间的跨会话记忆存储（长期记忆）

命名空间设计:
    - 长期记忆(InMemoryStore): namespace = (user_id, session_id)
    - 短期记忆(checkpointer):   通过 thread_id 区分不同对话线程
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import AsyncGenerator, Any

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from config.prompts.agents.memory_prompt import SUMMARY_EXTRACTION_PROMPT, MEMORY_INJECTION_SYSTEM_TEMPLATE
from config.settings import llm

logger = logging.getLogger(__name__)

# ============================================================
# 全局单例：Checkpointer 和 MemoryStore 实例
# ============================================================

def _get_checkpointer() -> InMemorySaver:
    """获取全局唯一的 checkpointer 实例（管理短期/工作记忆）"""
    if not hasattr(_get_checkpointer, "_instance"):
        _get_checkpointer._instance = InMemorySaver()
    return _get_checkpointer._instance


def _get_memory_store() -> InMemoryStore:
    """获取全局唯一的 memory_store 实例（管理长期/结论记忆）"""
    if not hasattr(_get_memory_store, "_instance"):
        _get_memory_store._instance = InMemoryStore()
    return _get_memory_store._instance


@dataclass
class RuntimeContext:
    """运行时上下文 —— 标识一次完整对话的全部维度
    
    Attributes:
        project_name: 项目名称
        module_id:    模块ID
        user_id:      用户标识（用于长期记忆命名空间第一维，隔离不同用户）
        session_id:   会话ID（用于长期记忆命名空间第二维，区分同一用户的多次会话）
        thread_id:    会话线程ID（用于 checkpointer 区分同一会话内的不同对话流）
    """
    project_name: str
    module_id: str
    user_id: str | None = None
    session_id: str | None = None
    thread_id: str | None = None


class DualMemoryManager:
    """双记忆系统管理器
    
    核心能力：
      - [读取侧] 长期记忆加载 + 去重注入 + System Message 组装
      - [写入侧] LLM 摘要提取 → 结构化存储 → 异步后台保存
      - [清理侧] 会话级记忆清除 + 注入状态重置
    
    使用方式：
        memory = DualMemoryManager()
        messages = await memory.prepare_messages(context, query)   # 准备消息
        # ... 执行 agent.stream() ...
        asyncio.create_task(memory.save_after_turn(context, query, response))  # 后台保存
    """

    # 类级别集合：记录已注入过长期记忆的 thread_id（保证每个会话只注入一次）
    _injected_threads: set[str] = set()

    def __init__(self):
        self.checkpointer = _get_checkpointer()     # 短期记忆：会话内多轮自动管理
        self.memory_store = _get_memory_store()      # 长期记忆：跨会话结构化存储

    # ==================== 【读取侧】====================

    def should_inject(self, context: RuntimeContext) -> bool:
        """判断是否需要注入长期记忆
        
        规则：同一个 thread_id 只注入一次，避免重复拼接历史导致消息膨胀
        """
        if context.thread_id is None:
            return False
        return context.thread_id not in self._injected_threads

    def mark_injected(self, thread_id: str):
        """标记该 thread_id 已完成长期记忆注入"""
        self._injected_threads.add(thread_id)

    def load_long_term_memories(self, context: RuntimeContext) -> list[dict]:
        """从 InMemoryStore 加载指定 namespace 下的所有长期记忆
        
        Args:
            context: 包含 user_id 和 session_id 的运行上下文
        
        Returns:
            长期记忆条目列表（每条为 dict 格式）
        """
        namespace = (context.user_id, context.session_id)
        items = self.memory_store.search(namespace)
        if items is None:
            return []
        return [item.value for item in items]

    def build_memory_system_message(self, memories: list[dict]) -> SystemMessage | None:
        """将长期记忆组装为 System Message
        
        Args:
            memories: 从 load_long_term_memories 返回的记忆条目列表
        
        Returns:
            如果有记忆内容则返回 SystemMessage，否则返回 None
        """
        if not memories:
            return None

        # 格式化记忆内容为可读文本
        memory_lines = []
        for idx, mem in enumerate(memories, 1):
            summary = mem.get("result_summary", "无摘要")
            history = mem.get("history_summaries", [])
            detail = "; ".join(history) if history else ""
            memory_lines.append(f"  [{idx}] {summary}" + (f" | 详情: {detail}" if detail else ""))

        memory_content = "\n".join(memory_lines)
        formatted_prompt = MEMORY_INJECTION_SYSTEM_TEMPLATE.format(memory_content=memory_content)
        
        return SystemMessage(content=formatted_prompt)

    async def prepare_messages(
        self,
        context: RuntimeContext,
        query: str,
    ) -> dict[str, list]:
        """准备 Agent 输入消息 —— 核心入口方法
        
        流程：
          Step 0: 注入项目上下文（每次都注入，确保LLM感知当前项目）
          Step 1: 判断是否需要注入长期记忆（按 thread_id 去重）
          Step 2: 如需注入 → 加载全部历史记忆 → 组装 System Message 放在消息头部
          Step 3: 追加用户当前问题
        
        Args:
            context: 运行上下文
            query:   用户本轮输入的问题
        
        Returns:
            {"messages": [SystemMessage(项目上下文), SystemMessage(可选), HumanMessage, ...]} 格式的字典
        """
        from langchain_core.messages import AIMessage, SystemMessage as _SysMsg

        messages = []

        # ---- Step 0: 每次对话都注入项目上下文（让LLM知道当前项目）----
        project_context_msg = self._build_project_context_message(context)
        if project_context_msg:
            messages.append(project_context_msg)

        # ---- Step 1 & 2: 首次调用 → 注入完整长期记忆 ----
        if self.should_inject(context):
            logger.info(f"[长期记忆注入] 开始为 thread_id={context.thread_id} 加载历史记忆")
            memories = self.load_long_term_memories(context)
            sys_msg = self.build_memory_system_message(memories)
            
            if sys_msg:
                messages.append(sys_msg)
                logger.info(f"[长期记忆注入] 成功注入 {len(memories)} 条历史记忆")
            else:
                logger.info("[长期记忆注入] 无历史记忆，跳过注入")
            
            # 标记已注入，后续同 thread_id 改用轻量模式
            self.mark_injected(context.thread_id)

        # ---- Step 3: 追加用户当前问题 ----
        messages.append(HumanMessage(content=query))

        return {"messages": messages}

    def _build_project_context_message(self, context: RuntimeContext) -> SystemMessage | None:
        """构建项目上下文系统消息
        
        让 LLM 在每轮对话中都能感知到当前工作项目的名称和模块信息，
        避免出现"请告诉我项目名称是什么"这类不必要的追问。
        
        Args:
            context: 包含 project_name 和 module_id 的运行时上下文
            
        Returns:
            包含项目信息的 SystemMessage；如果信息不足则返回 None
        """
        parts = []
        
        # 项目名称（必填）
        if context.project_name and context.project_name.strip():
            parts.append(f"- **当前项目**: {context.project_name}")
        else:
            return None  # 项目名是必须的
            
        # 模块ID（可选）
        if context.module_id and context.module_id.strip() and context.module_id != "None":
            parts.append(f"- **模块标识**: {context.module_id}")
            
        if not parts:
            return None
            
        content = (
            f"【当前工作环境】\n"
            + "\n".join(parts)
            + "\n\n"
            + "重要提示：你已经在上述项目中工作，无需再次询问项目名称。"
            + "直接基于用户输入的需求/指令执行任务即可。"
        )
        
        return SystemMessage(content=content)

    # ==================== 【写入侧】====================

    async def extract_summary(self, query: str, response: str) -> dict:
        """调用 LLM 从 Q&A 中提取结构化摘要
        
        Args:
            query:    用户问题
            response: AI 完整回答
        
        Returns:
            结构化摘要字典（包含 action_type, result_summary 等字段）
        
        Note:
            LLM 提取失败时会抛异常，由调用方 fallback 处理
        """
        prompt = SUMMARY_EXTRACTION_PROMPT.format(query=query, response=response)
        result = await llm.ainvoke(prompt)
        
        try:
            # 清理 LLM 可能包裹的 markdown 代码块标记
            text = result.content.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"[摘要提取] LLM 返回的 JSON 解析失败: {e}, 使用降级方案")
            raise

    @staticmethod
    def fallback_summary(query: str, response: str) -> dict:
        """降级兜底方案：当 LLM 提取失败时使用规则生成简单摘要
        
        Args:
            query:    用户问题
            response: AI 回答
        
        Returns:
            基础结构的摘要字典
        """
        return {
            "action_type": "unknown",
            "target_module": "",
            "result_summary": response[:100] + ("..." if len(response) > 100 else ""),
            "pending_items": [],
            "completed_items": [],
            "history_summaries": [f"Q: {query[:50]}..."]
        }

    def save_long_term_memory(self, context: RuntimeContext, summary: dict):
        """将摘要写入 InMemoryStore（长期记忆持久化）
        
        Args:
            context: 运行上下文（用于构建 namespace）
            summary: 待存储的结构化摘要
        """
        namespace = (context.user_id, context.session_id)
        key = str(uuid.uuid4())       # 每条记忆唯一标识
        self.memory_store.put(namespace, key, summary)
        logger.info(f"[长期记忆保存] namespace={namespace}, key={key}")

    async def save_after_turn(self, context: RuntimeContext, query: str, response: str):
        """每轮对话结束后的保存操作 —— 异步后台执行
        
        流程：
          Step 1: 调用 LLM 提取摘要（失败则降级）
          Step 2: 写入 InMemoryStore
        
        设计意图：
          此方法通过 asyncio.create_task() 在后台异步执行，
          不阻塞主流程的流式响应速度。
        
        Args:
            context: 运行上下文
            query:    用户本轮问题
            response: AI 本轮完整回答
        """
        try:
            # ---- Step 1: LLM 提取结构化摘要 ----
            summary = await self.extract_summary(query, response)
        except Exception as e:
            logger.warning(f"[摘要提取] LLM 提取失败，启用降级方案: {e}")
            summary = self.fallback_summary(query, response)

        # ---- Step 2: 写入长期记忆存储 ----
        self.save_long_term_memory(context, summary)

    # ==================== 【清理侧】====================

    def clear_session_memory(self, context: RuntimeContext):
        """清除指定会话的所有长期记忆
        
        用途：用户主动清空会话历史、或会话过期时清理
        
        Args:
            context: 运行上下文（user_id + session_id 定位目标命名空间）
        """
        namespace = (context.user_id, context.session_id)
        # InMemoryStore 的 search 返回的是 StoreItem 列表，逐条删除
        items = self.memory_store.search(namespace)
        if items:
            for item in items:
                self.memory_store.delete((item.namespace, item.key))
            logger.info(f"[记忆清理] 已清除 namespace={namespace} 下 {len(items)} 条记忆")

    @classmethod
    def reset_injection_state(cls, thread_id: str | None = None):
        """重置长期记忆注入状态
        
        Args:
            thread_id: 指定重置某个 thread_id；若为 None 则全部重置
        
        用途：
          - 新建会话前确保能重新注入
          - 测试环境重置状态
        """
        if thread_id is None:
            cls._injected_threads.clear()
            logger.info("[状态重置] 已清除所有 thread_id 的注入记录")
        else:
            cls._injected_threads.discard(thread_id)
            logger.info(f"[状态重置] 已清除 thread_id={thread_id} 的注入记录")
