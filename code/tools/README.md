# 04-action-tools — 工具执行层配套代码

IoT 企业 诊断工具集演示。实现统一工具接口 `tool.run(input) -> dict`，包含设备状态查询和历史告警检索两个工具，在 `MOCK_MODE=true` 下无需真实 AWS 后端。

对应文档：[工具执行层](../../docs/docs/04-action-tools/index.md)

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `iot_tools.py` | DeviceStatusTool + AlarmHistoryTool 实现与演示 |
| `requirements.txt` | Python 依赖（MOCK 模式无需安装）|

---

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `MOCK_MODE` | `false` | `true` 时使用内置 Mock 数据 |
| `AWS_REGION` | `us-east-1` | AWS 区域 |
| `IOT_ENDPOINT` | AWS IoT URL | IoT Core 端点（MOCK_MODE=false 时使用）|
| `ALARM_TABLE` | `iot-agent-alarms` | DynamoDB 告警表名 |

---

## 运行演示

```bash
MOCK_MODE=true python iot_tools.py
```

---

## 与文档的对应关系

| 代码模块 | 文档章节 |
|---------|---------|
| `BaseTool` 接口 | [工具设计原则](../../docs/docs/04-action-tools/tool-design.md) |
| `DeviceStatusTool` | [工具执行层 §IoT 场景](../../docs/docs/04-action-tools/index.md) |
| `AlarmHistoryTool` | [工具执行层 §IoT 场景](../../docs/docs/04-action-tools/index.md) |
