# Đối chiếu yêu cầu chặng A với implementation

| Năng lực | Code chính | Kiểm thực tế |
| --- | --- | --- |
| Đăng nhập/session/CSRF/role/tenant | backend/app/security.py, main.py, models.py | test_stage01_api.py, test_csrf_header.py |
| Template 51 câu, 16 CORE, nhánh theo loại/ngôn ngữ | backend/app/questions.json, questionnaire.py; frontend/app/page.tsx | catalog/branch tests + browser |
| Structured delivery/language/deadline/approval/budget/rights | questionnaire.py, ValueEditor trong page.tsx | semantic tests, final-audit scope cases |
| Câu trả lời có trạng thái, revision, evidence | models.Answer, main.save_answer/confirm | no-auto-confirm, forbidden-status/actor/role, source provenance |
| Nháp không đầy đủ, thiếu/mâu thuẫn/tư vấn | questionnaire.evaluate, frontend panels | malformed input + conflict/consultation tests |
| Nguồn gốc, parse, prefill đề xuất | models.Source, main.extract_source/prefill | upload/security/tamper/manual fallback + browser upload |
| Không đếm attempt thành video | questionnaire.delivery_matrix | quantity/variant tests |
| Scope theo đầu ra, giữ dữ liệu branch cũ | valid_scope_ids/annotate_answers | orphan/hidden/global-ID/scope override regressions |
| Xác nhận có người có quyền | main.confirm, session actor | ACCOUNT/VIEWER denied, PM/Admin confirmation |
| Review, feedback, thay đổi | main.feedback/submit; page review UI | feedback, full browser review |
| Snapshot/hash/approval bất biến | main.snapshot_payload/verify_snapshot/decide | wrong hash/version, immutable export/history |
| Concurrency không mất dữ liệu | SELECT FOR UPDATE và CAS Project.revision | PostgreSQL two-writer test: một 200/một 409 |
| Stage02 chỉ nhận input còn hiệu lực | main.stage02/handoff | approval/stale/hash/tenant tests + browser |
| Folder Thông Tin/Word/PDF/JSON | backend/app/exports.py | ZIP byte checksums, actual formats, Unicode VI/JP |
| Lưu bền, schema migration và chạy local | db.py, models.py, migrations/, compose.yaml, scripts/manage.py | PostgreSQL migration, services smoke, DB riêng QA |

Đây là mapping phần đã triển khai Stage 01. Không coi các module media/credit/AE của hệ thống tổng thể là đã có chỉ vì giao diện có tên stage tương ứng. AI prefill tổng quát, OCR và S3 adapter chưa được triển khai; fallback hiện được ghi rõ ở UI/docs.
