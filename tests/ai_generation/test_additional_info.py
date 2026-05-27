from service.ai_generation.common import (
    LLM_NOT_CONFIGURED_MSG,
    api_test_gen_use_mock,
    build_default_additional_info,
    functional_gen_use_mock,
    is_llm_configured,
)
from service.core import config as core_config


def test_build_default_additional_info_uses_config_default():
    info = build_default_additional_info()
    assert info == {"notice": core_config.AI_GENERATION_DEFAULT_NOTICE}


def test_build_default_additional_info_env_override(monkeypatch):
    monkeypatch.setenv("AI_GENERATION_DEFAULT_NOTICE", "自定义脚本提示")
    monkeypatch.setattr(
        core_config,
        "AI_GENERATION_DEFAULT_NOTICE",
        "自定义脚本提示",
    )
    info = build_default_additional_info()
    assert info["notice"] == "自定义脚本提示"


def test_llm_helpers_with_mock_env(monkeypatch):
    monkeypatch.delenv("LLM_BINDING_API_KEY", raising=False)
    monkeypatch.delenv("FUNCTIONAL_GEN_MOCK", raising=False)
    monkeypatch.delenv("API_TEST_GEN_MOCK", raising=False)
    assert is_llm_configured() is False
    assert functional_gen_use_mock() is False
    assert api_test_gen_use_mock() is False
    assert LLM_NOT_CONFIGURED_MSG
