import errno
import socket

import httpx
import pytest

from app.diagnostics import overpass_connectivity as diagnostic


class RespondingAsyncClient:
    def __init__(self, response):
        self.response = response
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url, **kwargs):
        self.requests.append((url, kwargs))
        return self.response


class FailingAsyncClient:
    def __init__(self, error):
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, *_args, **_kwargs):
        raise self.error


@pytest.mark.asyncio
async def test_diagnostic_probes_both_hosts_with_fixed_query_and_logs_status(
    monkeypatch, capsys
):
    endpoints = (
        "https://current.example/api/interpreter",
        "https://mirror.example/api/interpreter",
    )
    response = httpx.Response(
        503,
        request=httpx.Request("POST", endpoints[0]),
        text="must not be logged",
    )
    clients = []

    def create_client(**_kwargs):
        client = RespondingAsyncClient(response)
        clients.append(client)
        return client

    monkeypatch.setattr(
        diagnostic.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    )
    monkeypatch.setattr(diagnostic.httpx, "AsyncClient", create_client)

    await diagnostic.run_diagnostic(endpoints)

    output = capsys.readouterr().out
    assert "endpoint_host=current.example" in output
    assert "endpoint_host=mirror.example" in output
    assert output.count("dns_result=resolved") == 2
    assert output.count("connection_outcome=response_received") == 2
    assert output.count("http_status=503") == 2
    assert "exception_class=unavailable errno=unavailable" in output
    assert "must not be logged" not in output
    assert len(clients) == 2
    for client in clients:
        assert client.requests[0][1]["data"] == {"data": diagnostic.TEST_QUERY}
        assert "latitude" not in diagnostic.TEST_QUERY
        assert "longitude" not in diagnostic.TEST_QUERY


@pytest.mark.asyncio
async def test_diagnostic_logs_sanitized_dns_failure_without_http_request(
    monkeypatch, capsys
):
    def fail_dns(*_args, **_kwargs):
        raise socket.gaierror(socket.EAI_NONAME, "sensitive DNS detail")

    def unexpected_client(**_kwargs):
        pytest.fail("HTTP client must not be created when DNS fails")

    monkeypatch.setattr(diagnostic.socket, "getaddrinfo", fail_dns)
    monkeypatch.setattr(diagnostic.httpx, "AsyncClient", unexpected_client)

    await diagnostic.run_diagnostic(("https://private.example/api/interpreter",))

    output = capsys.readouterr().out
    assert (
        output.strip()
        == "overpass_diagnostic endpoint_host=private.example "
        "dns_result=resolution_failed connection_outcome=not_attempted "
        f"http_status=unavailable exception_class=gaierror errno={socket.EAI_NONAME}"
    )
    assert "sensitive" not in output


@pytest.mark.asyncio
async def test_diagnostic_logs_sanitized_connection_failure(monkeypatch, capsys):
    request = httpx.Request("POST", "https://current.example/api/interpreter")
    error = httpx.ConnectError("sensitive URL and request data", request=request)
    error.__cause__ = ConnectionRefusedError(errno.ECONNREFUSED, "sensitive socket detail")

    monkeypatch.setattr(
        diagnostic.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    )
    monkeypatch.setattr(
        diagnostic.httpx,
        "AsyncClient",
        lambda **_kwargs: FailingAsyncClient(error),
    )

    await diagnostic.run_diagnostic(("https://current.example/api/interpreter",))

    output = capsys.readouterr().out
    assert "endpoint_host=current.example" in output
    assert "dns_result=resolved" in output
    assert "connection_outcome=request_failed" in output
    assert "http_status=unavailable" in output
    assert "exception_class=ConnectError" in output
    assert f"errno={errno.ECONNREFUSED}" in output
    assert "sensitive" not in output
