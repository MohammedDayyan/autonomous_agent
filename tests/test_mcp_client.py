from __future__ import annotations

from ai_decision_os.mcp_client import MCPToolClient


def test_mcp_client_passes_environment_to_stdio_server(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")

    client = MCPToolClient()
    params = client._server_parameters()

    assert params.env is not None
    assert params.env["TAVILY_API_KEY"] == "tvly-test"
