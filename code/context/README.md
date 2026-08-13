# 06-context-engineering — 上下文工程配套代码

某企业 多设备并发诊断上下文调度演示。实现 GSSC 四阶段流水线（Gather → Select → Structure → Compress），在 `MOCK_MODE=true` 下模拟 10 台设备同时告警的上下文组装场景。

对应文档：[上下文工程](../../docs/docs/06-context-engineering/index.md)

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `gssc_pipeline.py` | GSSC 流水线 + Token 预算控制演示 |
| `requirements.txt` | Python 依赖 |

---

## 安装

```bash
pip install -r requirements.txt
```

> **MOCK_MODE=true 时 tiktoken 不是必须的**，缺少时会使用粗估（4 字符 ≈ 1 token）。

---

## 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `MOCK_MODE` | `false` | `true` 时使用内置 Mock 数据 |
| `TOKEN_BUDGET` | `4096` | Token 预算上限（触发压缩策略的阈值） |
| `MAX_DEVICES` | `10` | 模拟并发告警的设备数量 |

---

## 运行演示

```bash
# 默认 10 台设备，4096 Token 预算
MOCK_MODE=true python gssc_pipeline.py

# 模拟 20 台设备，8192 Token 预算
MOCK_MODE=true TOKEN_BUDGET=8192 MAX_DEVICES=20 python gssc_pipeline.py
```

---

## 与文档的对应关系

| 代码模块 | 文档章节 |
|---------|---------|
| `GSSCPipeline.gather` | [GSSC 流水线 §Gather 阶段](../../docs/docs/06-context-engineering/gssc-pipeline.md) |
| `GSSCPipeline.compress` | [上下文压缩策略](../../docs/docs/06-context-engineering/compression.md) |
| `TOKEN_BUDGET` 变量 | [Token 预算控制](../../docs/docs/07-cost-governance/token-budget.md) |
