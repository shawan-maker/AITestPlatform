import hashlib

from service.ai_generation.common import compute_prompt_hash, format_user_prompt_section


def test_format_user_prompt_section_none_or_blank():
    assert format_user_prompt_section(None) == ""
    assert format_user_prompt_section("") == ""
    assert format_user_prompt_section("   ") == ""
    assert format_user_prompt_section("\n\t") == ""


def test_format_user_prompt_section_with_text():
    assert format_user_prompt_section("  focus on login  ") == (
        "\n## 用户附加要求\nfocus on login\n"
    )


def test_compute_prompt_hash_without_user_prompt():
    source = "requirement body"
    expected = hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert compute_prompt_hash(source, None) == expected
    assert compute_prompt_hash(source, "") == expected
    assert compute_prompt_hash(source, "   ") == expected


def test_compute_prompt_hash_with_user_prompt():
    source = "requirement body"
    user_prompt = "extra rules"
    combined = f"{source}\n{user_prompt}"
    expected = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    assert compute_prompt_hash(source, user_prompt) == expected
    assert compute_prompt_hash(source, f"  {user_prompt}  ") == expected


def test_compute_prompt_hash_differs_when_user_prompt_changes():
    source = "same source"
    h1 = compute_prompt_hash(source, "prompt a")
    h2 = compute_prompt_hash(source, "prompt b")
    assert h1 != h2
