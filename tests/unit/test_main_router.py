import json

from src.handlers import main


def test_main_routes_health(monkeypatch):
    monkeypatch.setattr(main.health_check, "lambda_handler", lambda e, c: {"status": "ok"})
    event = {"requestContext": {"http": {"method": "GET", "path": "/health"}}}
    resp = main.lambda_handler(event, None)
    assert resp["status"] == "ok"


def test_main_routes_ticket_ingestion(monkeypatch):
    marker = {}

    def fake_handler(event, context):
        marker["called"] = True
        return {"statusCode": 200}

    monkeypatch.setattr(main.ticket_ingestion, "lambda_handler", fake_handler)
    event = {"requestContext": {"http": {"method": "POST", "path": "/tickets"}}}
    resp = main.lambda_handler(event, None)
    assert resp["statusCode"] == 200
    assert marker["called"] is True


def test_main_routes_context(monkeypatch):
    monkeypatch.setattr(main.customer_context, "lambda_handler", lambda e, c: {"ok": True})
    event = {"requestContext": {"http": {"method": "GET", "path": "/tickets/123/context"}}}
    resp = main.lambda_handler(event, None)
    assert resp["ok"] is True


def test_main_routes_feedback(monkeypatch):
    monkeypatch.setattr(main.ticket_ingestion, "feedback_handler", lambda e, c: {"fb": True})
    event = {"requestContext": {"http": {"method": "POST", "path": "/tickets/123/feedback"}}}
    resp = main.lambda_handler(event, None)
    assert resp["fb"] is True


def test_main_routes_kb_sync(monkeypatch):
    monkeypatch.setattr(main.kb_sync, "lambda_handler", lambda e, c: {"sync": True})
    event = {"requestContext": {"http": {"method": "POST", "path": "/kb/sync"}}}
    resp = main.lambda_handler(event, None)
    assert resp["sync"] is True


def test_main_unknown_route():
    event = {"requestContext": {"http": {"method": "GET", "path": "/unknown"}}}
    resp = main.lambda_handler(event, None)
    assert resp["statusCode"] == 404
    body = json.loads(resp["body"])
    assert body["message"] == "Route not found"
