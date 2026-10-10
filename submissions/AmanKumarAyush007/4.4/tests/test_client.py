from datetime import datetime, timedelta, timezone
import pytest
import responses
from scai_client import SCAIClient, SCAIClientConfig, SCAIAuthError, SCAINotFoundError, SCAIValidationError, SCAIAPIError

BASE = "https://scai.test"


@pytest.fixture
def client():
    client = SCAIClient(SCAIClientConfig(base_url=BASE, username="tester", password="secret", max_retries=0))
    yield client
    client.close()


def auth():
    responses.add(responses.POST, BASE + "/api/auth/token/", json={"access":"one", "refresh":"refresh", "expires_in":3600})


@responses.activate
def test_auto_login_on_first_request(client):
    auth(); responses.add(responses.GET, BASE + "/api/v1/call-logs/", json={"results":[]})
    assert client.list_call_logs()["results"] == []
    assert responses.calls[1].request.headers["Authorization"] == "Bearer one"


@responses.activate
def test_token_refresh_before_expiry(client):
    auth(); responses.add(responses.POST, BASE + "/api/auth/token/refresh/", json={"access":"two", "expires_in":3600})
    responses.add(responses.GET, BASE + "/api/v1/call-logs/", json={"results":[]})
    client.list_call_logs()
    client._token_manager._expires_at = datetime.now(timezone.utc) + timedelta(seconds=20)
    client.list_call_logs()
    assert responses.calls[-1].request.headers["Authorization"] == "Bearer two"


@responses.activate
def test_fallback_to_login_on_refresh_failure(client):
    auth(); responses.add(responses.POST, BASE + "/api/auth/token/refresh/", status=401)
    responses.add(responses.GET, BASE + "/api/v1/call-logs/", json={"results":[]})
    client.list_call_logs()
    client._token_manager._expires_at = datetime.now(timezone.utc)
    client.list_call_logs()
    assert len([call for call in responses.calls if call.request.url.endswith("/api/auth/token/")]) == 2


@responses.activate
def test_list_call_logs_returns_paginated(client):
    auth(); responses.add(responses.GET, BASE + "/api/v1/call-logs/", json={"count":1,"results":[{"id":1}]})
    assert client.list_call_logs(status="done", page=2)["count"] == 1
    assert "status=done" in responses.calls[-1].request.url


@responses.activate
def test_get_call_log_not_found_raises(client):
    auth(); responses.add(responses.GET, BASE + "/api/v1/call-logs/3/", status=404, json={"detail":"missing"})
    with pytest.raises(SCAINotFoundError): client.get_call_log(3)


@responses.activate
def test_create_call_log_returns_dict(client):
    auth(); responses.add(responses.POST, BASE + "/api/v1/call-logs/", status=201, json={"id":7})
    assert client.create_call_log("agent", "123", 10, "done")["id"] == 7


@responses.activate
def test_delete_call_log_returns_none(client):
    auth(); responses.add(responses.DELETE, BASE + "/api/v1/call-logs/7/", status=204)
    assert client.delete_call_log(7) is None


@responses.activate
def test_400_raises_validation_error(client):
    auth(); responses.add(responses.POST, BASE + "/api/v1/call-logs/", status=400, json={"status":["invalid"]})
    with pytest.raises(SCAIValidationError) as exc:
        client.create_call_log("x", "1", 0, "x")
    assert exc.value.errors["status"] == ["invalid"]


@responses.activate
def test_500_raises_api_error(client):
    auth(); responses.add(responses.GET, BASE + "/api/v1/call-logs/", status=500, json={"detail":"broken"})
    with pytest.raises(SCAIAPIError): client.list_call_logs()


@responses.activate
def test_401_triggers_token_login(client):
    auth(); responses.add(responses.GET, BASE + "/api/v1/call-logs/", status=401)
    responses.add(responses.GET, BASE + "/api/v1/call-logs/", json={"results":[]})
    assert client.list_call_logs() == {"results":[]}
    assert len([call for call in responses.calls if call.request.url.endswith("/api/auth/token/")]) == 2


def test_invalid_config():
    with pytest.raises(ValueError): SCAIClientConfig(base_url="ftp://example.com", username="x", password="y")


@responses.activate
def test_update_call_log(client):
    auth(); responses.add(responses.PATCH, BASE + "/api/v1/call-logs/1/", json={"notes":"updated"})
    assert client.update_call_log(1, notes="updated")["notes"] == "updated"


def test_reject_invalid_id(client):
    with pytest.raises(ValueError): client.get_call_log(0)
