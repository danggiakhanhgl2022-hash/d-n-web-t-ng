def test_non_ascii_csrf_header_is_denied_without_server_error(api):
    response = api.client.post("/api/v1/projects", json={"name": "QA CSRF", "customer": "QA"},
                               headers=[(b"X-CSRF-Token", b"\xe9")])
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_INVALID"
