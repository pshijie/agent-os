# Module:   08-protocols / MCP Demo
# Ref:      hello-agents/code/chapter10/mcp
# Scenario: 某企业 多 Agent 协作通信协议演示（MCP 简化版）
# Deps:     (MOCK_MODE=true 时无外部依赖)
# Run:      MOCK_MODE=true python mcp_demo.py

"""
Model Context Protocol (MCP) 简化版演示
=======================================
演示 MCP 的核心通信模式：
- MCPClient:  发起工具调用请求
- MCPServer:  接收并路由工具调用，返回结构化响应
- MCPMessage: 标准化消息格式（JSON-RPC 2.0 风格）
在 MOCK_MODE=true 时完全在进程内运行，无需网络连接。
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

# ── 配置 ─────────────────────────────────────────────────────────────
MOCK_MODE: bool = os.environ.get("MOCK_MODE", "false").lower() == "true"
MCP_SERVER_URL: str = os.environ.get("MCP_SERVER_URL", "http://localhost:8080/mcp")


# ── MCP 消息格式（JSON-RPC 2.0 风格）────────────────────────────────
@dataclass
class MCPRequest:
    """MCP 工具调用请求（对应 JSON-RPC 2.0 Request）"""
    method: str                      # 工具名，格式: "tools/call"
    params: dict[str, Any]           # {"name": "tool_name", "arguments": {...}}
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    jsonrpc: str = "2.0"

    def to_dict(self) -> dict:
        return {"jsonrpc": self.jsonrpc, "id": self.id,
                "method": self.method, "params": self.params}


@dataclass
class MCPResponse:
    """MCP 工具调用响应（对应 JSON-RPC 2.0 Response）"""
    id: str
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    jsonrpc: str = "2.0"

    @property
    def is_error(self) -> bool:
        return self.error is not None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error:
            d["error"] = self.error
        else:
            d["result"] = self.result
        return d


# ── MCP Server ────────────────────────────────────────────────────────
class MCPServer:
    """
    简化版 MCP Server：注册工具并路由工具调用请求。
    生产版对应 Amazon Bedrock AgentCore 的 MCP Server 集成。
    """

    def __init__(self, server_name: str) -> None:
        self.server_name = server_name
        self._tools: dict[str, Callable] = {}
        self._tool_schemas: dict[str, dict] = {}

    def register_tool(
        self, name: str, description: str,
        input_schema: dict, func: Callable
    ) -> None:
        """注册工具及其 JSON Schema 描述"""
        self._tools[name] = func
        self._tool_schemas[name] = {
            "name": name,
            "description": description,
            "inputSchema": {"type": "object", "properties": input_schema},
        }

    def list_tools(self) -> list[dict]:
        """返回所有注册工具的 Schema 列表（对应 MCP tools/list 方法）"""
        return list(self._tool_schemas.values())

    def handle(self, request: MCPRequest) -> MCPResponse:
        """路由并处理 MCP 请求"""
        if request.method == "tools/list":
            return MCPResponse(id=request.id, result={"tools": self.list_tools()})

        if request.method == "tools/call":
            tool_name = request.params.get("name", "")
            arguments = request.params.get("arguments", {})
            if tool_name not in self._tools:
                return MCPResponse(
                    id=request.id,
                    error={"code": -32601, "message": f"工具 '{tool_name}' 不存在"},
                )
            try:
                result = self._tools[tool_name](**arguments)
                return MCPResponse(id=request.id, result={"content": result})
            except Exception as exc:
                return MCPResponse(
                    id=request.id,
                    error={"code": -32603, "message": f"工具执行失败: {exc}"},
                )

        return MCPResponse(
            id=request.id,
            error={"code": -32600, "message": f"不支持的方法: {request.method}"},
        )


# ── MCP Client ────────────────────────────────────────────────────────
class MCPClient:
    """
    简化版 MCP Client：向 MCP Server 发送工具调用请求。
    生产版对应 Amazon Bedrock Agents 内置的 MCP 客户端集成。
    """

    def __init__(self, server: MCPServer) -> None:
        # Mock 模式：直接调用 Server 实例（省略 HTTP 传输层）
        self._server = server

    def list_tools(self) -> list[dict]:
        """获取服务端可用工具列表"""
        req = MCPRequest(method="tools/list", params={})
        resp = self._server.handle(req)
        if resp.is_error:
            raise RuntimeError(f"list_tools 失败: {resp.error}")
        return resp.result.get("tools", [])

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """调用指定工具"""
        req = MCPRequest(
            method="tools/call",
            params={"name": tool_name, "arguments": arguments},
        )
        resp = self._server.handle(req)
        if resp.is_error:
            raise RuntimeError(f"工具调用失败: {resp.error}")
        return resp.result.get("content")


# ── Mock 工具实现 ─────────────────────────────────────────────────────
def tool_get_device_temperature(device_id: str) -> dict:
    mock_data = {"DEV-042": 68.5, "DEV-001": 34.1, "DEV-038": 41.2}
    temp = mock_data.get(device_id.upper(), None)
    if temp is None:
        return {"error": f"设备 {device_id} 不存在"}
    return {"device_id": device_id, "temperature_celsius": temp, "threshold": 60.0}


def tool_get_alarm_rule(alarm_type: str) -> dict:
    rules = {
        "OVER_TEMP": "§4.2 一级保护（60–75°C）：降低充电电流至额定值 50%，启动散热风扇 100%。",
        "UNDER_VOLTAGE": "§3.4.7 欠压保护（E047）：检查采样线，执行均衡充电。",
    }
    rule = rules.get(alarm_type.upper(), f"未找到 {alarm_type} 的处置规程")
    return {"alarm_type": alarm_type, "rule": rule}


# ── main ──────────────────────────────────────────────────────────────
def main() -> None:
    mode_label = "[MOCK]" if MOCK_MODE else "[LIVE]"
    print(f"\n{'='*60}")
    print(f"MCP 协议工具调用演示  {mode_label}")
    print(f"{'='*60}\n")

    try:
        # ── 初始化 MCP Server，注册 IoT 诊断工具 ────────────────────
        server = MCPServer("iot-company-iot-mcp-server")
        server.register_tool(
            name="get_device_temperature",
            description="查询 IoT 设备当前温度",
            input_schema={"device_id": {"type": "string", "description": "设备 ID"}},
            func=tool_get_device_temperature,
        )
        server.register_tool(
            name="get_alarm_rule",
            description="获取告警类型的处置规程",
            input_schema={"alarm_type": {"type": "string", "description": "告警类型（如 OVER_TEMP）"}},
            func=tool_get_alarm_rule,
        )

        client = MCPClient(server)

        # ── Step 1: 发现工具列表（tools/list）───────────────────────
        print("── Step 1: 工具发现（MCP tools/list）")
        tools = client.list_tools()
        for tool in tools:
            print(f"   {tool['name']}: {tool['description']}")

        # ── Step 2: 调用温度查询工具 ──────────────────────────────────
        print("\n── Step 2: 调用 get_device_temperature（DEV-042）")
        temp_result = client.call_tool("get_device_temperature", {"device_id": "DEV-042"})
        print(f"   结果: {json.dumps(temp_result, ensure_ascii=False)}")

        # ── Step 3: 调用规程查询工具 ──────────────────────────────────
        print("\n── Step 3: 调用 get_alarm_rule（OVER_TEMP）")
        rule_result = client.call_tool("get_alarm_rule", {"alarm_type": "OVER_TEMP"})
        print(f"   结果: {rule_result['rule']}")

        # ── Step 4: 调用不存在的工具（错误处理） ────────────────────
        print("\n── Step 4: 调用不存在的工具（错误处理验证）")
        try:
            client.call_tool("nonexistent_tool", {})
        except RuntimeError as e:
            print(f"   预期错误: {e}")

        print(f"\n{'='*60}")
        print("演示完成。MCP 协议在进程内模拟，无需网络连接。")
        print(f"{'='*60}\n")

    except Exception as exc:
        print(f"\n[ERROR] 演示运行失败: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
