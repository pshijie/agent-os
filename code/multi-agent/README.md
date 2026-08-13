# 10-multi-agent — 多智能体协作配套代码

某企业 多 Agent 协作演示。实现 Orchestrator-Worker 架构：协调器分解故障诊断请求，分发给温度分析、知识检索、报告生成三个 Worker Agent，最终聚合诊断报告。

对应文档：[多智能体协作](../../docs/docs/10-multi-agent/index.md)

---

## 运行演示

```bash
MOCK_MODE=true python orchestrator_demo.py
```

---

## 与文档的对应关系

| 代码模块 | 文档章节 |
|---------|---------|
| `OrchestratorAgent` | [Orchestrator 模式](../../docs/docs/10-multi-agent/orchestration.md) |
| `WorkerAgent` | [协作模式](../../docs/docs/10-multi-agent/collaboration.md) |
| `AgentMessage` | [通信协议](../../docs/docs/08-protocols/index.md) |
