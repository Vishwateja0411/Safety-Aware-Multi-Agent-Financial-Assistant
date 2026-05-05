from fastapi.testclient import TestClient

from src.app import app


def test_streaming_endpoint_returns_portfolio_health_events(load_user):
    client = TestClient(app)
    response = client.post(
        "/v1/chat/stream",
        json={
            "query": "how is my portfolio doing",
            "session_id": "test-http-portfolio",
            "user_context": load_user("usr_003"),
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert "event: metadata" in body
    assert '"agent":"portfolio_health"' in body
    assert "event: chunk" in body
    assert '"top_position":"NVDA"' in body
    assert "event: done" in body


def test_streaming_endpoint_blocks_before_routing():
    client = TestClient(app)
    response = client.post(
        "/v1/chat/stream",
        json={
            "query": "help me trade on this confidential merger news",
            "session_id": "test-http-safety",
            "user_context": {"positions": []},
        },
    )

    assert response.status_code == 200
    body = response.text
    assert '"blocked":true' in body
    assert '"safety_category":"insider_trading"' in body
    assert "event: done" in body


def test_streaming_endpoint_stubs_unimplemented_agents(load_user):
    client = TestClient(app)
    response = client.post(
        "/v1/chat/stream",
        json={
            "query": "what is the price of AAPL right now?",
            "session_id": "test-http-stub",
            "user_context": load_user("usr_001"),
        },
    )

    assert response.status_code == 200
    body = response.text
    assert '"agent":"market_research"' in body
    assert "not implemented in this MVP" in body
