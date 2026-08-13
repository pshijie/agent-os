# Module:   09-evaluation / Evaluation Metrics
# Ref:      hello-agents/code/chapter12/evaluation
# Scenario: 某企业 诊断 Agent 质量评估基线计算
# Deps:     (MOCK_MODE=true 时无外部依赖)
# Run:      MOCK_MODE=true python eval_metrics.py

"""
某企业 诊断 Agent 评估指标计算演示
=========================================
计算四项核心评估指标：
- task_completion_rate:  任务完成率（诊断成功率）
- tool_accuracy:         工具调用准确率（工具选择和参数正确性）
- avg_response_time_s:   平均响应延迟（秒）
- cost_efficiency:       成本效率（每成功诊断的 Token 消耗）
基于 mock 对话数据，无需真实 LLM 调用。
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any

# ── 配置 ─────────────────────────────────────────────────────────────
MOCK_MODE: bool = os.environ.get("MOCK_MODE", "false").lower() == "true"

# 某企业 评估基线目标值
BASELINE = {
    "task_completion_rate": 0.85,    # 目标 ≥ 85%
    "tool_accuracy": 0.90,           # 目标 ≥ 90%
    "avg_response_time_s": 30.0,     # 目标 ≤ 30s
    "cost_per_success_tokens": 2000, # 目标 ≤ 2000 tokens/次成功诊断
}


# ── 数据模型 ──────────────────────────────────────────────────────────
@dataclass
class DiagnosisRecord:
    """单次诊断对话记录"""
    session_id: str
    device_id: str
    completed: bool        # 是否成功给出诊断建议
    tool_calls: int        # 工具调用次数
    correct_tool_calls: int  # 工具调用正确次数（工具名和参数均正确）
    response_time_s: float   # 端到端响应延迟（秒）
    input_tokens: int
    output_tokens: int


# ── Metrics 计算 ──────────────────────────────────────────────────────
def compute_metrics(records: list[DiagnosisRecord]) -> dict[str, Any]:
    """
    计算评估指标集合。
    对标 某企业 诊断 Agent 质量基线（见文档 §IoT 场景）。
    """
    if not records:
        return {"error": "无评估记录"}

    n = len(records)
    n_completed = sum(1 for r in records if r.completed)
    total_tools = sum(r.tool_calls for r in records)
    correct_tools = sum(r.correct_tool_calls for r in records)
    total_tokens = sum(r.input_tokens + r.output_tokens for r in records)

    task_completion_rate = n_completed / n
    tool_accuracy = correct_tools / total_tools if total_tools > 0 else 0.0
    avg_response_time = sum(r.response_time_s for r in records) / n
    cost_per_success = total_tokens / n_completed if n_completed > 0 else float("inf")

    metrics = {
        "total_sessions": n,
        "task_completion_rate": round(task_completion_rate, 4),
        "tool_accuracy": round(tool_accuracy, 4),
        "avg_response_time_s": round(avg_response_time, 2),
        "cost_per_success_tokens": round(cost_per_success, 1),
        "total_tokens": total_tokens,
    }

    # 与基线对比
    baseline_check = {
        "task_completion_rate": task_completion_rate >= BASELINE["task_completion_rate"],
        "tool_accuracy": tool_accuracy >= BASELINE["tool_accuracy"],
        "avg_response_time_s": avg_response_time <= BASELINE["avg_response_time_s"],
        "cost_per_success_tokens": cost_per_success <= BASELINE["cost_per_success_tokens"],
    }
    metrics["baseline_pass"] = all(baseline_check.values())
    metrics["baseline_detail"] = {
        k: ("✅ 达标" if v else "❌ 未达标") for k, v in baseline_check.items()
    }

    return metrics


# ── Mock 数据 ─────────────────────────────────────────────────────────
MOCK_RECORDS = [
    DiagnosisRecord("s001", "DEV-042", True, 3, 3, 12.5, 1200, 350),
    DiagnosisRecord("s002", "DEV-038", True, 2, 2, 8.3, 900, 280),
    DiagnosisRecord("s003", "DEV-015", False, 3, 2, 45.0, 1800, 120),  # 超时未完成
    DiagnosisRecord("s004", "DEV-001", True, 2, 2, 9.1, 850, 300),
    DiagnosisRecord("s005", "DEV-042", True, 4, 4, 18.7, 1500, 420),
    DiagnosisRecord("s006", "DEV-100", True, 2, 1, 22.4, 1100, 310),   # 工具调用 1 次错误
    DiagnosisRecord("s007", "DEV-038", True, 3, 3, 14.2, 1300, 380),
    DiagnosisRecord("s008", "DEV-015", False, 2, 2, 38.5, 1600, 200),  # 超时
    DiagnosisRecord("s009", "DEV-001", True, 3, 3, 11.8, 1050, 320),
    DiagnosisRecord("s010", "DEV-042", True, 2, 2, 7.6, 800, 270),
]


# ── main ──────────────────────────────────────────────────────────────
def main() -> None:
    mode_label = "[MOCK]" if MOCK_MODE else "[LIVE]"
    print(f"\n{'='*60}")
    print(f"某企业 诊断 Agent 评估指标计算  {mode_label}")
    print(f"{'='*60}\n")

    try:
        # ── 计算指标 ────────────────────────────────────────────────
        print(f"── 评估数据集: {len(MOCK_RECORDS)} 条诊断会话记录")
        metrics = compute_metrics(MOCK_RECORDS)

        print(f"\n-- 评估结果")
        for key, val in metrics["baseline_detail"].items():
            status = "[OK]" if "达标" in val and "未" not in val else "[FAIL]"
            print(f"   {status} {key}: {metrics.get(key, '?')}")

        print(f"\n-- 总体结论")
        if metrics["baseline_pass"]:
            print("   [PASS] 所有指标达标，Agent 质量满足 某企业 生产部署基线。")
        else:
            fails = [k for k, v in metrics["baseline_detail"].items() if "未达标" in v]
            print(f"   [FAIL] {len(fails)} 项指标未达标: {fails}")
            print("   建议：检查未达标指标对应的模块并进行针对性优化。")

        print(f"\n{'='*60}")
        print("演示完成。基于 mock 对话数据，无需真实 LLM 调用。")
        print(f"{'='*60}\n")

    except Exception as exc:
        print(f"\n[ERROR] 演示运行失败: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
