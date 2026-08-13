# 01-memory — 记忆系统配套代码

某储能企业设备智能诊断 Agent 的记忆系统演示。覆盖**工作记忆**（带 TTL 的上下文缓存）和**情景记忆**（历史诊断案例存储与检索）两种记忆类型，可在 `MOCK_MODE=true` 下无 AWS 凭证独立运行。

对应文档：[记忆系统模块文档](../../docs/docs/01-memory/index.md)

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `memory_demo.py` | 主演示文件：工作记忆 + 情景记忆完整流程 |
| `requirements.txt` | Python 依赖（MOCK 模式无需安装）|
| `README.md` | 本文件 |

---

## 安装

```bash
# 创建虚拟环境（推荐）
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

> **MOCK_MODE=true 时无需安装任何依赖**，标准库即可运行完整演示。

---

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `MOCK_MODE` | `false` | 设为 `true` 时使用内置 Mock 数据，无需 AWS 凭证 |
| `WORKING_MEMORY_TTL` | `1800` | 工作记忆条目 TTL（秒），默认 30 分钟 |
| `WORKING_MEMORY_CAPACITY` | `50` | 工作记忆最大条目数，超限淘汰低重要性条目 |
| `EPISODIC_MEMORY_MAX` | `1000` | 情景记忆最大事件数 |
| `AWS_REGION` | `us-east-1` | AWS 区域（仅 MOCK_MODE=false 时使用）|
| `DYNAMODB_TABLE` | `iot-agent-episodic-memory` | DynamoDB 表名（仅 MOCK_MODE=false 时使用）|

---

## 运行演示

### 快速运行（Mock 模式，无需 AWS）

```bash
MOCK_MODE=true python memory_demo.py
```

预期输出：

```
============================================================
某企业 设备告警上下文管理演示  [MOCK]
============================================================

── Step 1: 写入历史诊断案例到情景记忆
   [a1b2c3d4] DEV-001 / over_temperature
   [e5f6g7h8] DEV-038 / over_temperature
   [i9j0k1l2] DEV-015 / under_voltage
   {'total_events': 3, 'max_size': 1000}

── Step 2: DEV-042 过温告警触发，写入工作记忆
   工作记忆快照: {'current_alarm': {...}, 'session_id': 'diag-session-dev042'}

── Step 3: 检索相似历史案例（Top-3）
   [1] DEV-001: 传感器单元 温度异常前兆，降低充电电流至额定值 50%
   [2] DEV-038: 温控系统散热不足，建议检查冷却风扇

── Step 4: 组装诊断上下文
   设备: DEV-042
   告警: over_temperature
   温度: 68.5°C
   诊断: [MOCK] 根据历史案例，建议降低充电电流至额定值 50% 并监控温度趋势。

── Step 5: 本次诊断写回情景记忆
   已记录事件 [m3n4o5p6]
   {'total_events': 4, 'max_size': 1000}
```

### 真实 AWS 模式

```bash
# 配置 AWS 凭证
export AWS_REGION=us-east-1
export DYNAMODB_TABLE=iot-agent-episodic-memory
# AWS 凭证通过 ~/.aws/credentials 或 IAM Role 注入，不在代码中硬编码

python memory_demo.py
```

> 真实模式需提前创建 DynamoDB 表，详见 [Amazon DynamoDB 文档](https://docs.aws.amazon.com/dynamodb/)。

---

## 与文档的对应关系

| 代码模块 | 文档章节 |
|---------|---------|
| `WorkingMemory` 类 | [工作记忆](../../docs/docs/01-memory/working.md) |
| `EpisodicMemory` 类 | [情景记忆](../../docs/docs/01-memory/episodic.md) |
| AWS 映射表 | [AWS AgentCore 对应](../../docs/docs/01-memory/working.md#7-aws-agentcore-对应) |
