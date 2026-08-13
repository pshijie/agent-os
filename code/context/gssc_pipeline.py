# Module:   06-context-engineering / GSSC Pipeline
# Ref:      hello-agents/code/chapter9/ContextBuilder
# Scenario: 某企业 多设备并发诊断上下文调度与 Token 预算控制
# Deps:     (MOCK_MODE=true 时无外部依赖)  tiktoken>=0.5 (optional)
# Run:      MOCK_MODE=true python gssc_pipeline.py

"""
某企业 多设备并发诊断上下文工程演示
==========================================
实现 GSSC 四阶段流水线：
- Gather  (收集)：从工作记忆、情景记忆、RAG 检索结果中汇总原始片段
- Select  (筛选)：按重要性和相关度排序，优先保留高价值片段
- Structure (结构化)：将片段组装为结构化 Prompt 模板
- Compress (压缩)：Token 预算控制，超限时截断低优先级内容
在 MOCK_MODE=true 时不依赖任何外部 API。
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any

# ── 配置 ─────────────────────────────────────────────────────────────
MOCK_MODE: bool = os.environ.get("MOCK_MODE", "false").lower() == "true"
TOKEN_BUDGET: int = int(os.environ.get("TOKEN_BUDGET", "4096"))
MAX_DEVICES: int = int(os.environ.get("MAX_DEVICES", "10"))

# 估算 Token 数（4 字符 ≈ 1 token，用于 Mock 模式）
def _estimate_tokens(text: str) -> int:
    try:
        import tiktoken  # type: ignore
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        return len(text) // 4  # 粗估


# ── 数据模型 ──────────────────────────────────────────────────────────
@dataclass
class ContextFragment:
    """上下文片段，携带来源、优先级和预估 Token 数"""
    source: str          # 来源标签（如 "working_memory", "episodic", "rag"）
    content: str         # 片段文本内容
    priority: float      # 优先级 0.0–1.0，越高越优先保留
    tokens: int = 0      # 预估 Token 数（自动计算）

    def __post_init__(self) -> None:
        if self.tokens == 0:
            self.tokens = _estimate_tokens(self.content)


# ── GSSC Pipeline ─────────────────────────────────────────────────────
class GSSCPipeline:
    """
    GSSC 上下文工程流水线：Gather → Select → Structure → Compress。
    类比：Java 流式处理（Stream.filter().sorted().collect()）。
    生产版本对应 Amazon Bedrock 上下文窗口管理 + Amazon Bedrock AgentCore 会话上下文。
    """

    def __init__(self, token_budget: int = TOKEN_BUDGET) -> None:
        self.token_budget = token_budget

    # ── 1. Gather ──────────────────────────────────────────────────────
    def gather(self, sources: dict[str, list[dict[str, Any]]]) -> list[ContextFragment]:
        """
        从多个来源（working_memory, episodic, rag）收集原始片段。
        sources: {"working_memory": [...], "episodic": [...], "rag": [...]}
        """
        fragments: list[ContextFragment] = []
        for source_name, items in sources.items():
            for item in items:
                frag = ContextFragment(
                    source=source_name,
                    content=item.get("content", ""),
                    priority=item.get("priority", 0.5),
                )
                fragments.append(frag)
        return fragments

    # ── 2. Select ─────────────────────────────────────────────────────
    def select(self, fragments: list[ContextFragment]) -> list[ContextFragment]:
        """
        按优先级降序排序，过滤掉空内容片段。
        类比：SQL ORDER BY priority DESC
        """
        return sorted(
            (f for f in fragments if f.content.strip()),
            key=lambda f: f.priority,
            reverse=True,
        )

    # ── 3. Structure ──────────────────────────────────────────────────
    def structure(self, fragments: list[ContextFragment], task: str) -> str:
        """
        将片段组装为结构化 Prompt 模板：
        [系统角色] + [当前任务] + [历史上下文] + [实时数据] + [知识库]
        """
        sections: dict[str, list[str]] = {
            "working_memory": [],
            "episodic": [],
            "rag": [],
            "other": [],
        }
        for frag in fragments:
            key = frag.source if frag.source in sections else "other"
            sections[key].append(frag.content)

        parts: list[str] = [
            "## 任务",
            task,
            "",
        ]
        if sections["working_memory"]:
            parts += ["## 当前告警上下文（工作记忆）",
                      "\n".join(sections["working_memory"]), ""]
        if sections["episodic"]:
            parts += ["## 历史诊断案例（情景记忆）",
                      "\n".join(sections["episodic"]), ""]
        if sections["rag"]:
            parts += ["## 设备手册相关规程（知识库）",
                      "\n".join(sections["rag"]), ""]
        if sections["other"]:
            parts += ["## 其他上下文", "\n".join(sections["other"]), ""]

        return "\n".join(parts)

    # ── 4. Compress ───────────────────────────────────────────────────
    def compress(self, context: str, fragments: list[ContextFragment]) -> str:
        """
        Token 预算控制：若组装后超出 token_budget，从低优先级片段开始截断。
        类比：JVM GC 的分代策略——优先回收低优先级对象。
        """
        total_tokens = _estimate_tokens(context)
        if total_tokens <= self.token_budget:
            return context

        # 超出预算：逐步移除最低优先级片段后重新组装
        sorted_frags = sorted(fragments, key=lambda f: f.priority)
        remaining = list(fragments)
        for frag in sorted_frags:
            if _estimate_tokens(context) <= self.token_budget:
                break
            remaining = [f for f in remaining if f is not frag]
            task_match = context.split("## 任务\n")[1].split("\n")[0] if "## 任务" in context else ""
            context = self.structure(remaining, task_match)

        return context

    def run(
        self,
        task: str,
        sources: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        """
        执行完整 GSSC 流水线，返回组装后的上下文和 Token 统计。
        """
        fragments = self.gather(sources)
        selected = self.select(fragments)
        structured = self.structure(selected, task)
        final = self.compress(structured, selected)
        final_tokens = _estimate_tokens(final)

        return {
            "context": final,
            "token_count": final_tokens,
            "token_budget": self.token_budget,
            "fragment_count": len(selected),
            "budget_used_pct": round(final_tokens / self.token_budget * 100, 1),
        }


# ── Mock 数据：10 台设备并发告警场景 ──────────────────────────────────
def build_mock_sources(device_count: int = MAX_DEVICES) -> dict[str, list[dict[str, Any]]]:
    """模拟 10 台设备同时告警时的上下文数据"""
    working_memory = [
        {
            "content": (
                f"设备 DMS-{100 + i:03d} 告警：过温 {60 + i * 1.5:.1f}°C "
                f"（阈值 60°C），SOC {75 + i:.1f}%"
            ),
            "priority": 0.9 - i * 0.05,  # 优先级递减，模拟重要性排序
        }
        for i in range(device_count)
    ]
    episodic = [
        {
            "content": (
                "历史案例 [2025-01-10]: DEV-042 过温处置——降低充电电流至额定值 50%，"
                "散热风扇 100%，30 分钟后温度恢复正常。"
            ),
            "priority": 0.8,
        },
        {
            "content": (
                "历史案例 [2024-12-05]: DEV-038 温度管理故障——散热风扇故障导致过温，"
                "更换风扇后恢复。"
            ),
            "priority": 0.7,
        },
    ]
    rag = [
        {
            "content": (
                "§4.2 设备温度保护规程：一级保护（60–75°C）——降低充电电流至额定值 50%，"
                "启动强制散热风扇（100%）。二级保护（≥75°C）——触发保护性断电。"
            ),
            "priority": 0.85,
        }
    ]
    return {"working_memory": working_memory, "episodic": episodic, "rag": rag}


# ── main ──────────────────────────────────────────────────────────────
def main() -> None:
    mode_label = "[MOCK]" if MOCK_MODE else "[LIVE]"
    print(f"\n{'='*60}")
    print(f"某企业 多设备并发上下文工程演示  {mode_label}")
    print(f"Token 预算: {TOKEN_BUDGET} tokens  设备数: {MAX_DEVICES}")
    print(f"{'='*60}\n")

    try:
        pipeline = GSSCPipeline(token_budget=TOKEN_BUDGET)
        task = "分析当前多台设备过温告警，按优先级给出处置建议。"
        sources = build_mock_sources(MAX_DEVICES)

        print("── Step 1: 执行 GSSC 流水线")
        result = pipeline.run(task=task, sources=sources)

        print(f"   片段数量:   {result['fragment_count']}")
        print(f"   Token 使用: {result['token_count']} / {result['token_budget']}"
              f"  ({result['budget_used_pct']}%)")
        if result['token_count'] > result['token_budget']:
            print("   [警告] 超出预算，已触发压缩策略")
        else:
            print("   [OK] 在预算范围内")

        print("\n── Step 2: 组装后的上下文预览（前 500 字符）")
        print(result["context"][:500] + ("..." if len(result["context"]) > 500 else ""))

        print(f"\n{'='*60}")
        print("演示完成。MOCK_MODE 下无需任何 AWS 凭证。")
        print(f"{'='*60}\n")

    except Exception as exc:
        print(f"\n[ERROR] 演示运行失败: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
