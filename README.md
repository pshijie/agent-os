<div align="center">

# Agent OS 知识库

**把 Agent 原理学透，再映射到 AWS AgentCore 落地 —— 一个 Java 工程师的 AI 系统工程笔记**

[![Deploy Status](https://img.shields.io/badge/deploy-vercel-black?logo=vercel)](https://agent-os-gilt.vercel.app)
[![Docusaurus](https://img.shields.io/badge/built%20with-Docusaurus%203-3ECC5F?logo=docusaurus)](https://docusaurus.io)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Theory: CoALA](https://img.shields.io/badge/theory-CoALA%202023-orange)](https://arxiv.org/abs/2309.02427)
[![Theory: AIOS](https://img.shields.io/badge/theory-AIOS%202024-purple)](https://arxiv.org/abs/2403.16971)

[**在线阅读 →**](https://agent-os-gilt.vercel.app) · [记忆系统](https://agent-os-gilt.vercel.app/docs/memory/index) · [RAG](https://agent-os-gilt.vercel.app/docs/rag/index) · [规划推理](https://agent-os-gilt.vercel.app/docs/planning/index) · [多 Agent 协作](https://agent-os-gilt.vercel.app/docs/multi-agent/index)

</div>

---

## 这是什么

我是一名 Java 后端工程师，正在参与公司 Agent OS 的搭建，技术栈是 AWS AgentCore + Python。学习过程中发现一个普遍的断层：

> **教程讲原理，官方文档讲 API，中间那层"原理 → 代码实现 → 云服务落地"的映射，几乎没人系统讲清楚。**

这个仓库是我填这个断层的笔记。以 [hello-agents](https://github.com/DjangoPeng/hello-agents) 教程为学习主线，以一个 IoT 设备智能诊断 Agent 为贯穿业务场景，把每个 Agent OS 模块的**理论 → 代码 → AWS 映射**三层结构对齐，形成可持续维护的专业文档站。

---

## 理论基础

框架基于两篇论文，不绑定任何厂商定义：

| 论文 | 贡献 |
|------|------|
| [CoALA](https://arxiv.org/abs/2309.02427)（普林斯顿/MIT，2023） | 定义四种记忆类型（Working / Episodic / Semantic / Perceptual）、行动空间、决策过程 |
| [AIOS](https://arxiv.org/abs/2403.16971)（Rutgers，2024） | 将 Agent OS 类比为操作系统内核，定义调度、上下文管理、存储管理等六大子系统 |

---

## 内容地图

```
Agent OS
├── 01 记忆系统        工作记忆 / 情景记忆 / 语义记忆 / 感知记忆
├── 02 感知与输入      多模态输入处理（草稿中）
├── 03 规划与推理      ReAct / Plan-and-Solve / Reflection
├── 04 工具执行层      统一工具接口 / 注册 / 执行路由
├── 05 RAG 检索增强    检索流水线 / 知识库构建
├── 06 上下文工程      GSSC 流水线 / Token 压缩策略
├── 07 成本治理        Token 预算 / 成本监控 / Bedrock 定价
├── 08 通信协议        MCP / A2A
├── 09 评估体系        四维指标 / 质量基线
└── 10 多 Agent 协作   Orchestrator 模式 / Worker 专业化
```

每个模块包含：

- **理论**：CoALA / AIOS 原文引用，不是二手转述
- **代码**：来自 hello-agents 源码的关键片段，附行级中文注释
- **IoT 场景**：以一个设备诊断 Agent 为例，贯穿所有模块的具体应用
- **AWS 映射**：本地实现 → Amazon Bedrock AgentCore 的精确对应表
- **可运行代码**：`code/` 目录下，`MOCK_MODE=true` 即可运行，无需 AWS 凭证

---

## 快速开始

**在线阅读**（推荐）：直接访问 [agent-os-gilt.vercel.app](https://agent-os-gilt.vercel.app)

**本地运行**：

```bash
git clone https://github.com/<你的用户名>/agent-os-docs.git
cd agent-os-docs/docs
npm install
npm start
# 打开 http://localhost:3000
```

**运行配套代码**（以记忆系统为例）：

```bash
cd code/memory
MOCK_MODE=true python memory_demo.py
```

所有 `code/` 下的示例都支持 `MOCK_MODE=true`，不依赖 AWS 凭证即可完整演示逻辑。

---

## 项目结构

```
agent-os/
├── docs/                    # Docusaurus 3 文档站
│   └── docs/
│       ├── intro.md         # Agent OS 全景总览
│       ├── 01-memory/       # 记忆系统（5 篇）
│       ├── 03-planning/     # 规划与推理（4 篇）
│       ├── 05-rag/          # RAG 检索增强（3 篇）
│       └── ...              # 共 10 个模块，30+ 篇文档
├── code/                    # 配套 Python 示例代码
│   ├── memory/              # 工作记忆 + 情景记忆演示
│   ├── rag/                 # RAG 流水线演示
│   ├── planning/            # ReAct Agent 演示
│   ├── tools/               # IoT 诊断工具演示
│   ├── context/             # GSSC 流水线演示
│   ├── cost/                # Token 成本追踪演示
│   ├── protocols/           # MCP 协议演示
│   ├── evaluation/          # 评估指标计算演示
│   └── multi-agent/         # Orchestrator-Worker 演示
├── scripts/
│   └── test_doc_compliance.py  # 文档合规性测试（P1-P5）
├── vercel.json              # Vercel 部署配置
└── _template.md             # 模块文档标准模板（九章节）
```

---

## IoT 诊断场景示例

文档中的代码示例使用一个 IoT 设备诊断 Agent 作为贯穿场景，以下是 ReAct 推理链的演示输出：

```
任务: 设备 DEV-042 上报过温告警，请诊断并给出处置建议。

── Step 1 ──
Thought: 先查询设备当前实时状态，确认告警真实性。
Action: query_device_status[DEV-042]
Observe: temperature=68.5°C, threshold=60.0°C, status=ALARM

── Step 2 ──
Thought: 温度超阈值，查阅设备手册的处置规程。
Action: search_manual[设备过温处置规程]
Observe: §4.2 一级保护：降低充电电流至额定值 50%，启动散热风扇。

── Step 3 ──
Action: Finish[建议：降低充电电流至额定值 50%，启动强制散热（100% 风速）。
              持续监控，若 5 分钟内未降温，触发保护性断电。]
```

---

## 技术栈

| 层 | 选型 |
|----|------|
| 文档框架 | Docusaurus 3 + MDX |
| 交互架构图 | React Flow |
| 时序/流程图 | Mermaid |
| 部署 | Vercel |
| 配套代码 | Python 3.10+，无 LangChain / LlamaIndex |
| AWS 技术栈 | Amazon Bedrock AgentCore |

---

## 文档质量保证

所有文档遵循统一的九章节模板，由自动化脚本持续验证：

```bash
python scripts/test_doc_compliance.py
```

```
✅ P1 frontmatter 合规性（31 个文件）
✅ P2 mock 模式可运行性（9 个代码文件）
✅ P3 无硬编码 secrets
✅ P4 无禁止依赖（无 langchain/llama-index）
✅ P5 必需正文章节（IoT 场景 / AWS 映射 / 相关模块）
```

---

## 参考资料

- [hello-agents — 《从零开始构建智能体》](https://github.com/DjangoPeng/hello-agents)（主要学习来源）
- [CoALA 论文](https://arxiv.org/abs/2309.02427) — Cognitive Architectures for Language Agents
- [AIOS 论文](https://arxiv.org/abs/2403.16971) — LLM Agent Operating System
- [Amazon Bedrock AgentCore 文档](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)

---

<div align="center">

如果这个仓库对你有帮助，欢迎 Star ⭐ — 它能帮助更多工程师找到从 Agent 原理到 AWS 落地的路径。

</div>
