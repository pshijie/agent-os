# Module:   05-rag / RAG Pipeline
# Ref:      hello-agents/code/chapter8/04_RAGTool_MarkItDown_Pipeline.py
# Scenario: 某储能企业设备手册知识库构建与设备故障问答
# Deps:     (MOCK_MODE=true 时无外部依赖)  boto3>=1.34 (optional)
# Run:      MOCK_MODE=true python rag_pipeline.py

"""
某企业 设备手册知识库问答演示
====================================
演示 RAG 检索流水线的核心机制：
- DocumentChunker: 将设备手册文本分块
- VectorIndex:     内存向量索引（Mock 版用关键词相似度；生产版用 Amazon Knowledge Bases）
- RAGPipeline:     摄取 + 查询完整流程
在 MOCK_MODE=true 时不依赖任何外部 API 即可完整运行演示。
"""

from __future__ import annotations

import os
import re
import sys
import hashlib
from dataclasses import dataclass, field
from typing import Any

# ── 配置 ─────────────────────────────────────────────────────────────
MOCK_MODE: bool = os.environ.get("MOCK_MODE", "false").lower() == "true"
CHUNK_SIZE: int = int(os.environ.get("CHUNK_SIZE", "512"))
CHUNK_OVERLAP: int = int(os.environ.get("CHUNK_OVERLAP", "50"))
TOP_K: int = int(os.environ.get("TOP_K", "3"))

# AWS 配置（仅 MOCK_MODE=false 时使用）
AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")
KNOWLEDGE_BASE_ID: str = os.environ.get("KNOWLEDGE_BASE_ID", "")
EMBEDDING_MODEL_ARN: str = os.environ.get(
    "EMBEDDING_MODEL_ARN",
    "arn:aws:bedrock:us-east-1::foundation-model/amazon.titan-embed-text-v2:0",
)


# ── 数据模型 ──────────────────────────────────────────────────────────
@dataclass
class Chunk:
    """文档分块，携带原始文本和元数据"""
    chunk_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResult:
    """检索结果，包含分块内容和相关度分数"""
    chunk: Chunk
    score: float


# ── DocumentChunker ───────────────────────────────────────────────────
class DocumentChunker:
    """
    将原始文档文本切割为固定大小的分块。
    生产版本对应 Amazon Bedrock Knowledge Bases 的 FIXED_SIZE / HIERARCHICAL 分块策略。
    """

    def __init__(self, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size    # 每块最大字符数
        self.overlap = overlap          # 相邻块重叠字符数，避免语义在边界断裂

    def chunk(self, text: str, doc_id: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """将文本切割为带重叠的固定大小分块，返回 Chunk 列表"""
        meta = metadata or {}
        chunks: list[Chunk] = []
        start = 0
        idx = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk_id = hashlib.md5(f"{doc_id}:{idx}".encode()).hexdigest()[:8]
                chunks.append(Chunk(
                    chunk_id=chunk_id,
                    text=chunk_text,
                    metadata={**meta, "doc_id": doc_id, "chunk_idx": idx},
                ))
                idx += 1
            start = end - self.overlap if end < len(text) else len(text)
        return chunks


# ── VectorIndex ───────────────────────────────────────────────────────
class VectorIndex:
    """
    内存向量索引（Mock 版：关键词重叠相似度；生产版：替换为 Amazon OpenSearch kNN）。
    类比：搜索引擎倒排索引 / Elasticsearch knn_vector 字段。
    """

    def __init__(self) -> None:
        self._chunks: list[Chunk] = []

    def add(self, chunks: list[Chunk]) -> None:
        """批量写入分块到索引"""
        self._chunks.extend(chunks)

    def search(self, query: str, top_k: int = TOP_K) -> list[SearchResult]:
        """检索最相关的 top_k 分块（Mock 版用关键词重叠评分）"""
        if MOCK_MODE or not KNOWLEDGE_BASE_ID:
            return self._keyword_search(query, top_k)
        return self._aws_search(query, top_k)

    def _keyword_search(self, query: str, top_k: int) -> list[SearchResult]:
        """基于关键词重叠的 Mock 相似度检索（演示用）"""
        query_tokens = set(re.findall(r'\w+', query.lower()))
        scored: list[tuple[float, Chunk]] = []
        for chunk in self._chunks:
            chunk_tokens = set(re.findall(r'\w+', chunk.text.lower()))
            overlap = len(query_tokens & chunk_tokens)
            if overlap > 0:
                score = overlap / (len(query_tokens) + 1e-6)  # 简化 Jaccard 系数
                scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [SearchResult(chunk=c, score=s) for s, c in scored[:top_k]]

    def _aws_search(self, query: str, top_k: int) -> list[SearchResult]:
        """真实 AWS Amazon Bedrock Knowledge Bases 检索（需配置 KNOWLEDGE_BASE_ID）"""
        try:
            import boto3  # type: ignore
            client = boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)
            resp = client.retrieve(
                knowledgeBaseId=KNOWLEDGE_BASE_ID,
                retrievalQuery={"text": query},
                retrievalConfiguration={"vectorSearchConfiguration": {"numberOfResults": top_k}},
            )
            results = []
            for r in resp.get("retrievalResults", []):
                chunk = Chunk(
                    chunk_id=r.get("location", {}).get("s3Location", {}).get("uri", "unknown"),
                    text=r["content"]["text"],
                    metadata=r.get("metadata", {}),
                )
                results.append(SearchResult(chunk=chunk, score=r.get("score", 0.0)))
            return results
        except Exception as exc:
            print(f"[ERROR] AWS 检索失败: {exc}", file=sys.stderr)
            return self._keyword_search(query, top_k)  # 降级到 Mock 检索

    def stats(self) -> dict[str, int]:
        return {"total_chunks": len(self._chunks)}


# ── RAGPipeline ───────────────────────────────────────────────────────
class RAGPipeline:
    """
    完整 RAG 流水线：文档摄取 + 查询检索。
    生产版对应 Amazon Bedrock Knowledge Bases 托管流水线。
    """

    def __init__(self) -> None:
        self.chunker = DocumentChunker()
        self.index = VectorIndex()

    def ingest(self, text: str, doc_id: str, metadata: dict[str, Any] | None = None) -> int:
        """摄取文档：分块 → 写入索引，返回新增分块数"""
        chunks = self.chunker.chunk(text, doc_id, metadata)
        self.index.add(chunks)
        return len(chunks)

    def query(self, question: str, top_k: int = TOP_K) -> list[SearchResult]:
        """查询：检索最相关分块，返回 SearchResult 列表"""
        return self.index.search(question, top_k)

    def stats(self) -> dict[str, int]:
        return self.index.stats()


# ── Mock 设备手册数据 ──────────────────────────────────────────────────
MOCK_MANUAL_SECTIONS = {
    "bms-e047": {
        "doc_id": "bms-error-codes-v3.2",
        "text": (
            "设备错误代码 E047 — 单体电池欠压保护（Cell Under-Voltage Protection）\n"
            "触发条件：任意单体电池电压低于 欠压阈值 阈值持续 5 秒以上。\n"
            "系统动作：系统触发一级保护，立即停止放电，发出 Level-2 告警。\n"
            "处置步骤：\n"
            "  1. 检查 设备采样线是否松动或接触不良。\n"
            "  2. 使用万用表确认对应电池单体实际电压。\n"
            "  3. 若实际电压正常（>2.90V），可能为采样电路故障，联系售后。\n"
            "  4. 若实际电压确实偏低，执行均衡充电程序（参见第 6.3 节）。\n"
            "复位条件：所有单体电压恢复至 复位电压 以上后，可手动复位 DMS。"
        ),
        "metadata": {"section": "3.4.7", "device_model": "DEVICE-2000", "version": "3.2"},
    },
    "over-temperature": {
        "doc_id": "thermal-management-v2.1",
        "text": (
            "4.2 设备温度保护规程（Battery Temperature Protection）\n"
            "一级保护（60°C ≤ T < 75°C）：\n"
            "  • 系统自动降低充电电流至额定值 50%\n"
            "  • 启动强制散热风扇（风速 100%）\n"
            "  • 上报 DMS-04x 系列告警码\n"
            "二级保护（T ≥ 75°C）：\n"
            "  • 系统触发保护性断电，停止所有设备设备充放电操作\n"
            "  • 现场人员应立即检查散热系统，确认无温度异常迹象\n"
            "  • 24 小时内联系 某企业 技术支持\n"
            "温度传感器失效处理：若温度读数突变为 -40°C 或 200°C，判定为传感器故障，\n"
            "按 E063 错误码处理（参见第 3.4.9 节）。"
        ),
        "metadata": {"section": "4.2", "device_model": "DEVICE-2000", "version": "2.1"},
    },
    "charging-spec": {
        "doc_id": "bess-installation-manual-v4.0",
        "text": (
            "5.3 充电参数规格（MODEL-A 电池型号）\n"
            "标准充电电流：额定值（最大连续充电电流）\n"
            "快充电流上限：额定值 150%（环境温度 15–35°C，持续时长 ≤ 2 小时）\n"
            "充电截止电压：额定截止电压 / 单体（±10mV 容差）\n"
            "充电截止温度：45°C（超过此温度 系统自动降额至 额定值 30%）\n"
            "推荐浮充电压：浮充电压 / 单体（满电后保持）\n"
            "SOC 保护范围：10%–95%（超出范围 DMS 限制设备设备充放电）"
        ),
        "metadata": {"section": "5.3", "device_model": "DEVICE-2000", "version": "4.0"},
    },
}


# ── main ──────────────────────────────────────────────────────────────
def main() -> None:
    mode_label = "[MOCK]" if MOCK_MODE else "[LIVE]"
    print(f"\n{'='*60}")
    print(f"某企业 设备手册知识库问答演示  {mode_label}")
    print(f"{'='*60}\n")

    try:
        pipeline = RAGPipeline()

        # ── Step 1: 摄取设备手册文档 ──────────────────────────────────
        print("── Step 1: 摄取设备手册文档到知识库")
        for section_key, section in MOCK_MANUAL_SECTIONS.items():
            n = pipeline.ingest(
                text=section["text"],
                doc_id=section["doc_id"],
                metadata=section["metadata"],
            )
            print(f"   [{section['doc_id']}] {n} 个分块写入索引")
        print(f"   {pipeline.stats()}\n")

        # ── Step 2: 设备故障问答演示 ───────────────────────────────────
        demo_queries = [
            "DMS E047 错误代码如何处理？",
            "设备过温 68.5 度应该怎么办？",
            "MODEL-A 电池充电截止电压是多少？",
        ]

        print("── Step 2: 设备故障问答（RAG 检索）")
        for question in demo_queries:
            results = pipeline.query(question, top_k=TOP_K)
            print(f"\n   问题: {question}")
            if results:
                best = results[0]
                # 截取前 200 字展示
                snippet = best.chunk.text[:200].replace("\n", " ")
                print(f"   来源: {best.chunk.metadata.get('doc_id', 'unknown')} "
                      f"§{best.chunk.metadata.get('section', '?')}")
                print(f"   相关度: {best.score:.3f}")
                print(f"   片段: {snippet}...")
            else:
                print("   未找到相关内容")

        print(f"\n{'='*60}")
        print("演示完成。MOCK_MODE 下不依赖任何 AWS 资源。")
        print(f"{'='*60}\n")

    except Exception as exc:
        print(f"\n[ERROR] 演示运行失败: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
