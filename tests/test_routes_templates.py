"""Integration tests for the templates API routes."""

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("sqlalchemy")


class TestListTemplates:
    def test_includes_default(self, client):
        resp = client.get("/api/templates")
        assert resp.status_code == 200
        templates = resp.json()
        assert len(templates) >= 1
        default = [t for t in templates if t["is_default"]]
        assert len(default) == 1
        assert default[0]["name"] == "Default Extraction"


class TestGetTemplate:
    def test_get_default(self, client):
        resp = client.get("/api/templates")
        default_id = [t for t in resp.json() if t["is_default"]][0]["id"]
        resp = client.get(f"/api/templates/{default_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "prompt_text" in data
        assert "schema" in data

    def test_not_found(self, client):
        resp = client.get("/api/templates/9999")
        assert resp.status_code == 404


class TestCreateTemplate:
    def test_create(self, client):
        resp = client.post("/api/templates", json={
            "name": "My Template",
            "description": "Custom extraction",
            "prompt_text": "Extract only topics",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My Template"
        assert data["is_default"] == 0
        assert "schema" in data

    def test_empty_name_rejected(self, client):
        resp = client.post("/api/templates", json={
            "name": "",
            "description": "",
            "prompt_text": "something",
        })
        assert resp.status_code == 400

    def test_empty_prompt_rejected(self, client):
        resp = client.post("/api/templates", json={
            "name": "Valid Name",
            "prompt_text": "",
        })
        assert resp.status_code == 400


class TestUpdateTemplate:
    def test_cannot_edit_default(self, client):
        resp = client.get("/api/templates")
        default_id = [t for t in resp.json() if t["is_default"]][0]["id"]
        resp = client.put(f"/api/templates/{default_id}", json={"name": "Hacked"})
        assert resp.status_code == 403

    def test_update_custom(self, client):
        # Create first
        resp = client.post("/api/templates", json={
            "name": "Editable",
            "description": "",
            "prompt_text": "prompt",
        })
        tid = resp.json()["id"]

        resp = client.put(f"/api/templates/{tid}", json={"name": "Updated Name"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"


class TestDeleteTemplate:
    def test_cannot_delete_default(self, client):
        resp = client.get("/api/templates")
        default_id = [t for t in resp.json() if t["is_default"]][0]["id"]
        resp = client.delete(f"/api/templates/{default_id}")
        assert resp.status_code == 403

    def test_delete_custom(self, client):
        resp = client.post("/api/templates", json={
            "name": "Deletable",
            "description": "",
            "prompt_text": "prompt",
        })
        tid = resp.json()["id"]
        resp = client.delete(f"/api/templates/{tid}")
        assert resp.status_code == 204

        resp = client.get(f"/api/templates/{tid}")
        assert resp.status_code == 404


class TestDuplicateTemplate:
    def test_duplicate(self, client):
        resp = client.post("/api/templates", json={
            "name": "Original",
            "description": "Desc",
            "prompt_text": "prompt text",
        })
        tid = resp.json()["id"]

        resp = client.post(f"/api/templates/{tid}/duplicate")
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Original (copy)"
        assert data["is_default"] == 0

    def test_duplicate_not_found(self, client):
        resp = client.post("/api/templates/9999/duplicate")
        assert resp.status_code == 404
