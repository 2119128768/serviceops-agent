from backend.llm.json_utils import extract_json_object


def test_extract_json_from_fenced_block():
    text = '```json\n{"intent": "api_quota_error"}\n```'
    assert extract_json_object(text) == {"intent": "api_quota_error"}


def test_extract_json_with_leading_text():
    text = '结果如下：\n{"supported_by_evidence": true, "unsupported_claims": []}\n请查收'
    parsed = extract_json_object(text)
    assert parsed["supported_by_evidence"] is True
    assert parsed["unsupported_claims"] == []


def test_extract_json_returns_empty_on_invalid():
    assert extract_json_object("不是 JSON") == {}
