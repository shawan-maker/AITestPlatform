"""AI用例生成模块 - meta

meta
"""
from service.ai_generation.schemas import AgentMetaOut, PromptTemplateItem
from service.core import settings as core_config

FUNCTIONAL_PROMPT_TEMPLATES: list[PromptTemplateItem] = [
    PromptTemplateItem(
        id="boundary",
        label="边界值",
        placeholder="重点覆盖边界值、空值、超长输入等场景",
    ),
    PromptTemplateItem(
        id="negative",
        label="异常流程",
        placeholder="重点覆盖非法参数、权限不足、重复提交等异常场景",
    ),
    PromptTemplateItem(
        id="regression",
        label="回归重点",
        placeholder="结合本次变更点，列出需要重点回归的功能模块",
    ),
]

API_PROMPT_TEMPLATES: list[PromptTemplateItem] = [
    PromptTemplateItem(
        id="auth",
        label="鉴权场景",
        placeholder="覆盖未登录、token 过期、越权访问等鉴权相关用例",
    ),
    PromptTemplateItem(
        id="params",
        label="参数校验",
        placeholder="覆盖必填缺失、类型错误、枚举非法值等参数校验场景",
    ),
    PromptTemplateItem(
        id="business",
        label="业务组合",
        placeholder="覆盖主流程成功路径及关键业务分支组合",
    ),
]


def get_agent_meta() -> AgentMetaOut:
    return AgentMetaOut(
        functional_prompt_templates=list(FUNCTIONAL_PROMPT_TEMPLATES),
        api_prompt_templates=list(API_PROMPT_TEMPLATES),
        single_interface_only=True,
        history_limit=core_config.AI_AGENT_SESSION_HISTORY_LIMIT,
    )
