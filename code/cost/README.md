# 07-cost-governance — 成本治理配套代码

某企业 诊断 Agent Token 成本追踪演示。实现 Token 计数中间件和成本累计追踪，模拟 10 台设备并发诊断的月度成本估算，在 `MOCK_MODE=true` 下无需任何 AWS 资源。

对应文档：[成本与资源治理](../../docs/docs/07-cost-governance/index.md)

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `token_tracker.py` | Token 计数中间件 + 成本累计追踪演示 |
| `requirements.txt` | Python 依赖（tiktoken 可选）|

---

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `MOCK_MODE` | `false` | `true` 时使用内置 Mock 数据 |
| `INPUT_PRICE_PER_1K` | `0.003` | 输入 Token 单价（$/1K tokens）|
| `OUTPUT_PRICE_PER_1K` | `0.015` | 输出 Token 单价（$/1K tokens）|
| `BEDROCK_MODEL_ID` | Claude 3 Sonnet | 模型 ID（影响价格参考标签）|

> ⚠️ 定价数据仅供参考，实际价格请以 [AWS Bedrock 定价页面](https://aws.amazon.com/bedrock/pricing/) 为准。

---

## 运行演示

```bash
MOCK_MODE=true python token_tracker.py
```

预期输出包含：每台设备的 Token 消耗明细、全局统计摘要、月度成本估算。

---

## 与文档的对应关系

| 代码模块 | 文档章节 |
|---------|---------|
| `TokenTracker` 类 | [成本监控](../../docs/docs/07-cost-governance/monitoring.md) |
| `count_tokens()` | [Token 预算控制](../../docs/docs/07-cost-governance/token-budget.md) |
| `monthly_estimate()` | [成本治理总览 §IoT 场景](../../docs/docs/07-cost-governance/index.md) |
