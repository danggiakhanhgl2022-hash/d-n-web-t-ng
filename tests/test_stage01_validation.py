"""Untrusted editable drafts must remain readable even before semantic correction."""
import pytest

from app.questionnaire import applicable_codes, delivery_matrix, evaluate, semantic_errors


MALFORMED_DRAFTS = [
    ("A7", None),
    ("A7", {"count": None}),
    ("A7", {"count": 42, "ratios": "9:16"}),
    ("A7", {"count": True, "ratios": [None, 1]}),
    ("A10", {"tracks": 42}),
    ("A10", {"tracks": {"TEXT": [None], "VOICE": 42, "SUB": "ja"}}),
    ("A12", {"assets": {"LOGO": [], "MUSIC": {}}}),
    ("A14", {"preview": [], "final": {}, "publish": 42}),
    ("A16", {"name": [], "mode": None}),
    ("A15", {"range": {}}),
    ("P3", {"v": [["SNS"]]}),
    ("D1", {"rows": "cảnh 4 bật mưa"}),
    ("D1", {"rows": [{"scope": "SCENE", "a": "4", "object": "LOGO", "detail": 5, "action": "KEEP"}]}),
    ("E1", {"v": ["1920 by 1080"]}),
    ("E11", {"amount": float("nan"), "rounds": -1}),
]


@pytest.mark.parametrize("code,value", MALFORMED_DRAFTS)
def test_untrusted_draft_json_is_validation_error_not_exception(code, value):
    assert semantic_errors(code, value), "Malformed contract should report semantic errors"
    answers = [{"question_code": code, "value": value, "status": "ANSWERED_UNCONFIRMED", "scope_id": ""}]
    assert isinstance(applicable_codes(answers), list)
    assert not evaluate(answers)["can_submit"]
    assert isinstance(delivery_matrix(answers), dict)


GARBAGE = [None, 0, -1, 1.5, True, "", "x", [], [None], [[]], {}, {"v": {}}, {"v": [{}]}, {"rows": [{"scope": [], "object": {}, "action": []}]},
           {"tracks": {"TEXT": {}, "VOICE": [[]]}}, {"assets": {"MUSIC": {}, "VOICE": []}}, {"_na": True}, {"_na": "yes"}]


def test_any_garbage_in_any_question_never_raises():
    """Mọi kiểu dữ liệu sai ở mọi câu đều chỉ ra lỗi, không làm sập kiểm tra hay bản xuất."""
    from app.questionnaire import QUESTIONS, answer_text
    for q in QUESTIONS:
        for value in GARBAGE:
            for other_field in ({}, {f["id"]: value for f in q["fields"]}):
                v = other_field or value
                semantic_errors(q["code"], v)
                answer_text(q["code"], v)
                answers = [{"question_code": q["code"], "value": v, "status": "ANSWERED_UNCONFIRMED", "scope_id": ""},
                           {"question_code": "A7", "value": v, "status": "CONFIRMED", "scope_id": ""}]
                evaluate(answers)
                delivery_matrix(answers)
