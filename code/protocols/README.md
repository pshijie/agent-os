# 08-protocols — 通信协议配套代码

MCP（Model Context Protocol）简化版演示。实现 MCPServer/MCPClient 核心通信模式，展示工具注册、发现、调用完整流程，在进程内运行无需网络连接。

对应文档：[通信协议](../../docs/docs/08-protocols/index.md)

---

## 运行演示

```bash
MOCK_MODE=true python mcp_demo.py
```

---

## 与文档的对应关系

| 代码模块 | 文档章节 |
|---------|---------|
| `MCPServer` | [MCP 协议](../../docs/docs/08-protocols/mcp.md) |
| `MCPClient` | [MCP 协议](../../docs/docs/08-protocols/mcp.md) |
| `MCPRequest/Response` | [通信协议总览](../../docs/docs/08-protocols/index.md) |
