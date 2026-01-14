from src.handlers import health_check


def test_health_check_returns_ok():
    resp = health_check.lambda_handler({}, None)
    assert resp["statusCode"] == 200
    assert "ok" in resp["body"]
