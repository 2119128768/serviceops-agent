from backend.llm.json_utils import extract_first_json_object, normalize_list_fields, safe_json_loads


def test_extract_first_json_object_handles_leading_text_and_braces_in_string():
    text = '说明：{"message":"value with } brace","items":["a"]} trailing'
    assert extract_first_json_object(text) == '{"message":"value with } brace","items":["a"]}'


def test_safe_json_loads_handles_fenced_json():
    parsed = safe_json_loads('```json\n{"ok": true, "items": "x"}\n```')
    assert parsed == {"ok": True, "items": "x"}


def test_normalize_list_fields_wraps_scalars_and_missing_values():
    normalized = normalize_list_fields({"missing_info": "account_id"}, ["missing_info", "required_tools"])
    assert normalized["missing_info"] == ["account_id"]
    assert normalized["required_tools"] == []

