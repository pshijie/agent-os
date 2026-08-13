---
title: "成本与资源治理（Cost Governance）"
sidebar_label: "成本与资源治理"
sidebar_position: 1
status: completed
tags: [cost-governance, token-budget, bedrock-pricing, iot]
last_updated: "2025-01-28"
---

# 成本与资源治理（Cost Governance）

> Agent OS 的"成本控制器"——Token 预算、API 限流、成本监控三位一体，确保 某企业 多设备并发诊断的月度 Bedrock 费用可预测、可控制。

---

## 理论基础

在 Agent OS 中，每次 LLM 推理调用都会消耗 Token，而 Token 直接对应 API 费用。与传统软件不同，Agent 的推理路径不固定——ReAct 的步骤数、Reflection 的迭代次数、GSSC 的上下文大小都会影响最终 Token 消耗，因此需要专门的成本治理层。

AIOS（Mei et al., 2024）在内核层定义了**访问控制子系统（Access Control Subsystem）**，负责对 LLM 调用进行速率限制和资源配额管理，这是成本治理的工程基础。

---

## Amazon Bedrock 定价模型

> ⚠️ 以下价格为参考值，实际价格请以 [AWS Bedrock 定价页面](https://aws.amazon.com/bedrock/pricing/) 为准，价格可能随时变动。

| 模型 | 输入 Token（$/1K） | 输出 Token（$/1K） | 上下文窗口 |
|------|-------------------|-------------------|-----------|
| Claude 3.5 Sonnet | $0.003 | $0.015 | 200K |
| Claude 3 Sonnet | $0.003 | $0.015 | 200K |
| Claude 3 Haiku | $0.00025 | $0.00125 | 200K |
| Amazon Titan Text Premier | $0.0008 | $0.0016 | 32K |

**成本构成**：每次诊断调用 = 输入 Token（系统提示 + 历史上下文 + 当前告警）× 输入单价 + 输出 Token（诊断建议）× 输出单价。

---

## IoT 场景：某企业 多设备成本估算

**业务参数**：

| 参数 | 值 |
|------|---|
| 部署设备数 | 500 台 |
| 平均每台设备每日告警 | 0.1 次（Level-2+） |
| 每次诊断 LLM 调用次数 | 3 次（ReAct 平均步数） |
| 每次调用平均输入 Token | 1500 |
| 每次调用平均输出 Token | 300 |

**月度成本估算公式**：

```
月度调用次数 = 500 台 × 0.1 次/天 × 30 天 × 3 次/诊断 = 4500 次
月度输入成本 = 4500 × 1500 / 1000 × $0.003 = $20.25
月度输出成本 = 4500 × 300 / 1000 × $0.015 = $20.25
月度总成本 ≈ $40.50（约 ¥295）
```

如需降低成本，可切换到 Claude 3 Haiku（约降低 90%），但需评估诊断质量是否满足基线。

---

## 子文档导航

| 文档 | 内容 |
|-----|------|
| [token-budget.md](./token-budget.md) | Token 预算中间件实现、预算分配策略 |
| [monitoring.md](./monitoring.md) | 成本监控、告警阈值、AWS Cost Explorer 集成 |

---

## AWS AgentCore 对应

| 本地实现 | AWS 组件 | 关键配置项 | 注意事项 |
|---------|---------|-----------|---------|
| Token 计数中间件 | [AWS Cost Explorer](https://docs.aws.amazon.com/cost-management/latest/userguide/what-is-costexplorer.html) + [Amazon CloudWatch](https://docs.aws.amazon.com/cloudwatch/) | Bedrock 使用量指标 | 需开启 Bedrock 的 CloudWatch 指标集成 |
| 预算告警 | [AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html) | `budgetLimit`, `notificationsWithSubscribers` | 设置月度预算告警，超 80% 时邮件通知 |
| API 限流 | [Amazon API Gateway](https://docs.aws.amazon.com/apigateway/) 速率限制 | `throttlingRateLimit`, `throttlingBurstLimit` | 在 Agent 前置 API Gateway，按设备 ID 限流 |

:::info 相关模块

- **[上下文工程](../06-context-engineering/index.md)**：上下文压缩（Compress 阶段）通过控制输入 Token 数直接降低成本。
- **[评估体系](../09-evaluation/index.md)**：评估指标中包含成本效率（Token/次成功诊断），两个模块联动优化。

:::

---

## 延伸阅读

- [AWS Bedrock 定价](https://aws.amazon.com/bedrock/pricing/)
- [AWS Budgets 文档](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html)
- [Amazon CloudWatch — Bedrock 指标](https://docs.aws.amazon.com/bedrock/latest/userguide/monitoring-cloudwatch.html)
- 配套代码：`code/cost/token_tracker.py`
