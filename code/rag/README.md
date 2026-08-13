# 05-rag — RAG 检索增强生成配套代码

某储能企业设备手册知识库问答演示。实现文档分块、内存向量索引（Mock 版）和检索查询，在 `MOCK_MODE=true` 下无 AWS 凭证独立运行。

对应文档：[RAG 检索增强生成](../../docs/docs/05-rag/index.md)

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `rag_pipeline.py` | 主演示文件：文档摄取 + 知识库问答 |
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
| `MOCK_MODE` | `false` | `true` 时使用内置 Mock 数据，无需 AWS 凭证 |
| `CHUNK_SIZE` | `512` | 文档分块大小（字符数） |
| `CHUNK_OVERLAP` | `50` | 相邻块重叠字符数 |
| `TOP_K` | `3` | 检索返回的最相关分块数 |
| `AWS_REGION` | `us-east-1` | AWS 区域（仅 MOCK_MODE=false 时使用）|
| `KNOWLEDGE_BASE_ID` | `""` | Amazon Bedrock Knowledge Bases ID |
| `EMBEDDING_MODEL_ARN` | Titan V2 ARN | 嵌入模型 ARN |

---

## 运行演示

### 快速运行（Mock 模式）

```bash
MOCK_MODE=true python rag_pipeline.py
```

预期输出：

```
============================================================
某企业 设备手册知识库问答演示  [MOCK]
============================================================

── Step 1: 摄取设备手册文档到知识库
   [bms-error-codes-v3.2] 1 个分块写入索引
   [thermal-management-v2.1] 1 个分块写入索引
   [bess-installation-manual-v4.0] 1 个分块写入索引
   {'total_chunks': 3}

── Step 2: 设备故障问答（RAG 检索）

   问题: DMS E047 错误代码如何处理？
   来源: bms-error-codes-v3.2 §3.4.7
   相关度: 0.600
   片段: 设备错误代码 E047 — 单体电池欠压保护...
```

### 真实 AWS 模式

```bash
export AWS_REGION=us-east-1
export KNOWLEDGE_BASE_ID=your-kb-id-here
python rag_pipeline.py
```

> 真实模式需提前在 Amazon Bedrock 控制台创建 Knowledge Base 并完成文档摄取。
> 详见 [Amazon Bedrock Knowledge Bases 文档](https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base.html)。

---

## 与文档的对应关系

| 代码模块 | 文档章节 |
|---------|---------|
| `DocumentChunker` 类 | [RAG 检索流水线 §分块策略](../../docs/docs/05-rag/pipeline.md) |
| `VectorIndex` 类 | [RAG 检索流水线 §HNSW 索引](../../docs/docs/05-rag/pipeline.md) |
| `RAGPipeline` 类 | [知识库构建](../../docs/docs/05-rag/knowledge-base.md) |
| AWS 映射表 | [RAG 检索流水线 §AWS AgentCore 对应](../../docs/docs/05-rag/pipeline.md#7-aws-agentcore-对应) |
