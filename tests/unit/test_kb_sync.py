import json
import os

import pytest

from src.handlers import kb_sync


@pytest.fixture(autouse=True)
def set_env(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "kb-123")
    monkeypatch.setenv("DATA_SOURCE_ID", "ds-456")


def test_kb_sync_starts_ingestion(monkeypatch):
    calls = {}

    class FakeClient:
        def start_ingestion_job(self, knowledgeBaseId, dataSourceId):
            calls["kb"] = knowledgeBaseId
            calls["ds"] = dataSourceId
            return {"ingestionJob": {"ingestionJobId": "job-789"}}

    monkeypatch.setattr(kb_sync, "client", FakeClient())

    resp = kb_sync.lambda_handler({}, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["job_id"] == "job-789"
    assert calls == {"kb": "kb-123", "ds": "ds-456"}


def test_kb_sync_handles_failure(monkeypatch):
    class BoomClient:
        def start_ingestion_job(self, knowledgeBaseId, dataSourceId):
            raise RuntimeError("bedrock down")

    monkeypatch.setattr(kb_sync, "client", BoomClient())

    resp = kb_sync.lambda_handler({}, None)
    assert resp["statusCode"] == 500
    body = json.loads(resp["body"])
    assert body["message"] == "KB sync failed"
