# 03-planning — 规划与推理配套代码

某储能企业设备故障诊断 ReAct Agent 演示。实现 Think → Act → Observe 推理循环，在 `MOCK_MODE=true` 下使用预定义脚本驱动推理，无需 AWS 凭证。

对应文档：[规划与推理](../../docs/docs/03-planning/index.md)

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `react_agent.py` | ReAct 范式故障诊断推理演示 |
| `requirements.txt` | Python 依赖（MOCK 模式无需安装）|

---

## 安装

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

> **MOCK_MODE=true 时无需安装任何依赖**，标准库即可运行完整演示。

---

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `MOCK_MODE` | `false` | `true` 时使用预定义推理脚本，无需 AWS 凭证 |
| `MAX_STEPS` | `10` | ReAct 最大推理步数（Circuit Breaker） |
| `AWS_REGION` | `us-east-1` | AWS 区域（仅 MOCK_MODE=false 时使用）|
| `BEDROCK_AGENT_ID` | `""` | Amazon Bedrock Agent ID |
| `BEDROCK_MODEL_ID` | Claude 3 Sonnet ARN | 底层 LLM 模型 ID |

---

## 运行演示

### 快速运行（Mock 模式）

```bash
MOCK_MODE=true python react_agent.py
```

预期输出：

```
============================================================
某企业 设备故障诊断 ReAct Agent 演示  [MOCK]
============================================================

   任务: DEV-042 设备上报过温告警，请诊断原因并给出处置建议。

   ── Step 1 ──
   Thought: 收到 DEV-042 过温告警，首先查询设备当前实时状态...
   Action: query_device_status[DEV-042]
   Observe: 设备状态:
     temperature: 68.5  threshold: 60.0  status: ALARM ...

   ── Step 2 ──
   Thought: 温度 68.5°C 已超阈值，查阅过温处置规程...
   Action: search_manual[设备过温处置规程]
   Observe: §4.2 一级保护：降低充电电流至额定值 50%...

   ── Step 3 ──
   Thought: 规程明确，执行一级处置...
   Action: Finish[...]

   ✅ 最终结论: 【诊断结论】DEV-042 设备过温...
```

### 真实 AWS 模式

```bash
export AWS_REGION=us-east-1
export BEDROCK_AGENT_ID=your-agent-id
export MOCK_MODE=false
python react_agent.py
```

> 真实模式需提前在 Amazon Bedrock 控制台创建 Agent 并配置 Action Groups。
> 详见 [Amazon Bedrock Agents 文档](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)。

---

## 与文档的对应关系

| 代码模块 | 文档章节 |
|---------|---------|
| `ReActAgent` 类 | [ReAct 范式](../../docs/docs/03-planning/react.md) |
| `ToolRegistry` 类 | [工具执行层](../../docs/docs/04-action-tools/index.md) |
| `MockLLM` 类 | [ReAct 范式 §实现要点](../../docs/docs/03-planning/react.md#5-实现要点代码示例) |
| AWS 映射表 | [ReAct 范式 §AWS AgentCore 对应](../../docs/docs/03-planning/react.md#7-aws-agentcore-对应) |
