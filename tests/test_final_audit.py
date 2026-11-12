"""Hồi quy cho bộ câu hỏi v3; gồm các tình huống phản chứng của kiểm toán QP-20 (U01–U13)."""
import copy

import pytest

from conftest import GOOD_ANSWERS, confirm_project, fill_project
from app.questionnaire import annotate_answers, canonical, evaluate, semantic_errors


def rows(*items):
    keys = ("scope", "a", "object", "detail", "action", "value")
    return {"rows": [dict(zip(keys, item)) for item in items]}


def answers_with(**overrides):
    values = copy.deepcopy(GOOD_ANSWERS)
    values.update(overrides)
    return [{"question_code": c, "value": v, "status": "CONFIRMED", "scope_id": ""} for c, v in values.items()]


def test_good_fixture_is_submittable():
    assert evaluate(answers_with())["can_submit"]


def test_scoped_answers_are_rejected_in_v3(api):
    project = api.project()
    response = api.put(f"/projects/{project['id']}/answers/A14", json={"expected_revision": project["revision"], "value": GOOD_ANSWERS["A14"], "status": "ANSWERED_UNCONFIRMED", "scope_id": "demo-del-01"})
    assert response.status_code == 422


def test_each_requirement_is_its_own_row_u01_u02_u06_u08():
    # Một câu ghép phải thành nhiều dòng; bảng D1 có đúng một đối tượng và một yêu cầu mỗi dòng.
    value = rows(("SCENE", 4, "LOGO", "Logo NATORI", "KEEP", ""), ("SCENE", 4, "CHARACTER", "Áo nhân vật A", "CHANGE", "Áo xanh"),
                 ("SCENE", 4, "SFX", "Tiếng mưa", "ON", ""))
    assert semantic_errors("D1", value) == []
    assert semantic_errors("D1", {"rows": [{"scope": "SCENE", "a": 4, "object": "LOGO", "detail": "", "action": "KEEP"}]})


@pytest.mark.parametrize("first,second", [("KEEP", "CHANGE"), ("ON", "OFF")])
def test_keep_change_and_on_off_conflicts_are_blocked_u11(first, second):
    value = rows(("SCENE", 4, "CHARACTER", "Áo nhân vật A", first, "Áo đỏ"),
                 ("SCENE", 4, "CHARACTER", "áo  nhân vật a", second, "Áo xanh"))
    assert any("mâu thuẫn" in e for e in semantic_errors("D1", value))


def test_different_characters_do_not_false_conflict():
    value = rows(("SCENE", 4, "CHARACTER", "Áo nhân vật A", "KEEP", ""), ("SCENE", 4, "CHARACTER", "Áo nhân vật B", "CHANGE", "Áo xanh"))
    assert semantic_errors("D1", value) == []


def test_two_different_change_values_conflict():
    value = rows(("SCENE", 2, "LOGO", "Màu logo", "CHANGE", "Xanh lá"), ("SCENE", 2, "LOGO", "màu logo", "CHANGE", "Xanh dương"))
    assert any("hai giá trị khác nhau" in e for e in semantic_errors("D1", value))


def test_change_requires_target_value():
    assert semantic_errors("D1", rows(("SCENE", 7, "CHARACTER", "Kiểu tóc", "CHANGE", "")))


def test_ratio_and_resolution_must_match_u13():
    result = evaluate(answers_with(A7={"count": 1, "ratios": ["9:16"]}, E1={"v": ["1920x1080"]}))
    assert not result["can_submit"]
    assert any(b["code"] == "CROSS_FIELD" and b["question_code"] == "E1" for b in result["blockers"])
    assert evaluate(answers_with(A7={"count": 1, "ratios": ["9:16", "16:9"]}, E1={"v": ["1080x1920", "OTHER"], "v__other": "1920x1080"}))["can_submit"]


def test_unclear_rights_block_and_claimed_rights_are_flagged_u12():
    blocked = evaluate(answers_with(E10={"status": "UNCLEAR", "evidence": "no license available"}))
    assert any(b["question_code"] == "E10" for b in blocked["blockers"])
    claimed = evaluate(answers_with(E10={"status": "CLAIMED", "evidence": "Khách nói đã có quyền"}))
    assert claimed["can_submit"] and any(c["question_code"] == "E10" for c in claimed["clarifications"])


def test_ai_video_without_ai_permission_is_a_conflict():
    result = evaluate(answers_with(P3={"v": ["AI"]}, A17={"v": "NO"}))
    assert any(b["question_code"] == "A17" and b["code"] == "CROSS_FIELD" for b in result["blockers"])


def test_not_applicable_only_where_allowed():
    assert semantic_errors("A13", {"_na": True}) == []
    assert semantic_errors("A3", {"_na": True})


def test_other_choice_needs_text():
    assert semantic_errors("A3", {"v": "OTHER"})
    assert semantic_errors("A3", {"v": "OTHER", "v__other": "Ra mắt sản phẩm"}) == []


def test_exclusive_options_cannot_mix():
    assert semantic_errors("P3", {"v": ["SNS", "UNSURE"]})
    assert semantic_errors("A10", {"tracks": {"TEXT": ["VI", "NONE"], "VOICE": ["NONE"], "SUB": ["NONE"]}})


def test_legacy_answers_are_kept_inactive():
    annotated = annotate_answers([{"question_code": "CORE-02", "value": "cũ", "status": "CONFIRMED", "scope_id": ""}])
    assert annotated[0]["applicable"] is False and annotated[0]["inactive_reason"] == "LEGACY_TEMPLATE"


def test_full_flow_submits_and_client_pdf_exports(api):
    project = confirm_project(api, fill_project(api, api.project()))
    assert project["validation"]["can_submit"], project["validation"]["blockers"]
    response = api.post(f"/projects/{project['id']}/submit", json={"expected_revision": project["revision"]})
    assert response.status_code == 200, response.text
    assert api.get(f"/projects/{project['id']}/package?format=client_pdf").content.startswith(b"%PDF-")


def test_brand_endpoint_exposes_shared_palette(api):
    brand = api.get("/brand").json()
    assert brand["colors"]["primary"].startswith("#") and brand["studio_name"]


@pytest.mark.parametrize("raw", ["NaN", "Infinity", "-Infinity", '{"amount":1e999}'])
def test_prefill_nonfinite_json_never_persists_nonfinite_values(api, raw):
    project = api.project()
    uploaded = api.post(f"/projects/{project['id']}/sources", data={"expected_revision": project["revision"]},
                        files={"file": ("nonfinite.txt", f"C2.1: {raw}".encode(), "text/plain")})
    assert uploaded.status_code == 201
    project = uploaded.json()
    response = api.post(f"/projects/{project['id']}/prefill", json={"expected_revision": project["revision"], "source_id": project["sources"][-1]["id"]})
    if raw.startswith("{"):
        assert response.status_code == 422, response.text
        assert api.get(f"/projects/{project['id']}").json()["answers"] == []
    else:
        assert response.status_code == 200, response.text
        answer = response.json()["answers"][0]
        assert answer["value"] == {"v": raw}
        assert answer["status"] == "PROPOSED_FROM_SOURCE"
        assert answer["confirmed_by"] is None


def test_canonical_rejects_unpaired_unicode_surrogate():
    with pytest.raises(UnicodeError):
        canonical({"value": "\ud800"})
