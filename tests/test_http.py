"""Offline tests for the HTTP layer - the upstream client is faked, no network."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from trademcp import http
from trademcp.http import DataSourceError
from trademcp.providers import yahoo


class _FakeResponse:
    """Just enough of an httpx response for the code under test."""

    def __init__(self, status_code: int = 200):
        self.status_code = status_code
        self.request = httpx.Request("GET", "https://example.test")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "boom", request=self.request, response=httpx.Response(self.status_code)
            )

    def json(self):
        # What httpx raises when the body is not JSON (an error page, say).
        raise ValueError("Expecting value: line 1 column 1 (char 0)")


class _FakeClient:
    def __init__(self, response=None, error: Exception | None = None):
        self._response = response
        self._error = error
        self.calls: list[str] = []

    async def get(self, url, params=None):
        self.calls.append(url)
        if self._error is not None:
            raise self._error
        return self._response


def _ready(client: _FakeClient):
    """An awaitable that hands back the fake client."""

    async def _get() -> _FakeClient:
        return client

    return _get()


class TestGetJson:
    def test_invalid_json_becomes_a_data_source_error(self, monkeypatch):
        client = _FakeClient(_FakeResponse())
        monkeypatch.setattr(http, "get_client", lambda: _ready(client))

        async def run():
            return await http.get_json("https://example.test", source="Test source")

        with pytest.raises(DataSourceError) as excinfo:
            asyncio.run(run())
        assert "not valid JSON" in str(excinfo.value)
        assert "Test source" in str(excinfo.value)

    def test_transport_error_is_reported_as_a_data_source_error(self, monkeypatch):
        client = _FakeClient(error=httpx.ReadTimeout("timed out"))
        monkeypatch.setattr(http, "get_client", lambda: _ready(client))

        async def run():
            return await http.get_json(
                "https://example.test", source="Test source", attempts=1
            )

        with pytest.raises(DataSourceError) as excinfo:
            asyncio.run(run())
        assert "Test source" in str(excinfo.value)
        assert "ReadTimeout" in str(excinfo.value)


class TestCrumb:
    def test_crumb_transport_error_becomes_a_data_source_error(self, monkeypatch):
        client = _FakeClient(error=httpx.ReadTimeout("timed out"))
        monkeypatch.setattr(yahoo, "get_client", lambda: _ready(client))
        monkeypatch.setattr(yahoo, "_crumb", None)

        async def run():
            return await yahoo._get_crumb()

        with pytest.raises(DataSourceError) as excinfo:
            asyncio.run(run())
        assert "crumb request failed" in str(excinfo.value)
        assert "ReadTimeout" in str(excinfo.value)
