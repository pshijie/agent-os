# Module:   07-cost-governance / Token Tracker
# Ref:      hello-agents/code/chapter9/token_budget
# Scenario: 某企业 多设备并发诊断 Token 消耗追踪与成本估算
# Deps:     (MOCK_MODE=true 时无外部依赖)  tiktoken>=0.5 (optional)
# Run:      MOCK_MODE=true python token_tracker.py

"""
某企业 诊断 Agent Token 成本追踪演示
==========================================
实现 Token 计数中间件和成本累计追踪：
- TokenCounter: 精确/粗估 Token 计数（可选 tiktoken）
- PricingConfig: Amazon Bedrock 模型定价配置（从环境变量读取）
- TokenTracker:  记录每次 LLM 调用的输入/输出 Token 数和累计成本
- main():        模拟 10 台设备诊断会话的成本汇总演示
在 MOCK_MODE=true 时不依赖任何外部 API。
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# ── 配置 ─────────────────────────────────────────────────────────────
MOCK_MODE: bool = os.environ.get("MOCK_MODE", "false").lower() == "true"

# Amazon Bedrock Claude 3 Sonnet 定价（美元/1000 tokens，参考 2025 年定价）
# 注意：价格可能随时变动，请以 https://aws.amazon.com/bedrock/pricing/ 为准
INPUT_PRICE_PER_1K: float = float(os.environ.get("INPUT_PRICE_PER_1K", "0.003"))
OUTPUT_PRICE_PER_1K: float = float(os.environ.get("OUTPUT_PRICE_PER_1K", "0.015"))
MODEL_ID: str = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")


# ── Token 计数 ────────────────────────────────────────────────────────
def count_tokens(text: str) -> int:
    """精确计数（tiktoken）或粗估（4 字符 ≈ 1 token）"""
    try:
        import tiktoken  # type: ignore
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        return max(1, len(text) // 4)


# ── 数据模型 ──────────────────────────────────────────────────────────
@dataclass
class LLMCall:
    """单次 LLM 调用记录"""
    session_id: str
    device_id: str
    input_tokens: int
    output_tokens: int
    model_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def cost_usd(self) -> float:
        """计算本次调用成本（美元）"""
        return (
            self.input_tokens / 1000 * INPUT_PRICE_PER_1K
            + self.output_tokens / 1000 * OUTPUT_PRICE_PER_1K
        )


# ── TokenTracker ──────────────────────────────────────────────────────
class TokenTracker:
    """
    Token 计数中间件，记录每次 LLM 调用并累计成本。
    类比：Java APM 埋点（Micrometer / Prometheus Counter）。
    生产版对应 AWS Cost Explorer + Amazon CloudWatch 自定义指标。
    """

    def __init__(self) -> None:
        self._calls: list[LLMCall] = []

    def record(
        self,
        session_id: str,
        device_id: str,
        input_text: str,
        output_text: str,
        model_id: str = MODEL_ID,
    ) -> LLMCall:
        """记录一次 LLM 调用，自动计算 Token 数和成本"""
        call = LLMCall(
            session_id=session_id,
            device_id=device_id,
            input_tokens=count_tokens(input_text),
            output_tokens=count_tokens(output_text),
            model_id=model_id,
        )
        self._calls.append(call)
        return call

    def summary(self) -> dict[str, Any]:
        """返回全局统计摘要"""
        total_input = sum(c.input_tokens for c in self._calls)
        total_output = sum(c.output_tokens for c in self._calls)
        total_cost = sum(c.cost_usd for c in self._calls)
        return {
            "total_calls": len(self._calls),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "total_cost_usd": round(total_cost, 6),
            "avg_cost_per_call_usd": round(total_cost / len(self._calls), 6) if self._calls else 0,
            "model_id": MODEL_ID,
        }

    def per_device_summary(self) -> dict[str, dict[str, Any]]:
        """按设备汇总 Token 消耗和成本"""
        result: dict[str, dict[str, Any]] = {}
        for call in self._calls:
            d = result.setdefault(call.device_id, {
                "calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0
            })
            d["calls"] += 1
            d["input_tokens"] += call.input_tokens
            d["output_tokens"] += call.output_tokens
            d["cost_usd"] = round(d["cost_usd"] + call.cost_usd, 6)
        return result

    def monthly_estimate(self, daily_alarm_rate: int = 50) -> dict[str, float]:
        """
        基于当前调用统计估算月度成本。
        daily_alarm_rate: 每日预期告警处理次数
        """
        if not self._calls:
            return {"monthly_cost_usd": 0.0}
        avg_cost = sum(c.cost_usd for c in self._calls) / len(self._calls)
        monthly_calls = daily_alarm_rate * 30
        return {
            "avg_cost_per_call_usd": round(avg_cost, 6),
            "daily_alarm_rate": daily_alarm_rate,
            "monthly_calls_estimate": monthly_calls,
            "monthly_cost_usd": round(avg_cost * monthly_calls, 2),
        }


# ── Mock 数据 ─────────────────────────────────────────────────────────
MOCK_DEVICE_SESSIONS = [
    {
        "device_id": f"DMS-{100 + i:03d}",
        "session_id": f"diag-session-{i:03d}",
        "input": (
            f"系统角色：你是 某储能企业设备诊断 Agent。\n"
            f"当前告警：设备 DMS-{100 + i:03d} 过温告警，温度 {60 + i * 1.5:.1f}°C。\n"
            f"历史案例：上次类似故障通过降低充电电流解决。\n"
            f"设备手册：§4.2 一级保护：降低充电电流至额定值 50%，启动散热风扇。\n"
            f"请给出诊断建议。"
        ),
        "output": (
            f"诊断结论：DMS-{100 + i:03d} 温度 {60 + i * 1.5:.1f}°C 超过阈值 60°C。\n"
            f"建议：① 降低充电电流至额定值 50%；② 启动强制散热风扇（100%）；③ 持续监控。\n"
            f"依据：§4.2 设备温度保护规程。"
        ),
    }
    for i in range(10)
]


# ── main ──────────────────────────────────────────────────────────────
def main() -> None:
    mode_label = "[MOCK]" if MOCK_MODE else "[LIVE]"
    print(f"\n{'='*60}")
    print(f"某企业 诊断 Agent Token 成本追踪演示  {mode_label}")
    print(f"模型: {MODEL_ID}")
    print(f"定价: 输入 ${INPUT_PRICE_PER_1K}/1K tokens  "
          f"输出 ${OUTPUT_PRICE_PER_1K}/1K tokens")
    print(f"{'='*60}\n")

    try:
        tracker = TokenTracker()

        # ── Step 1: 模拟 10 台设备诊断会话 ──────────────────────────
        print("── Step 1: 模拟 10 台设备诊断会话的 Token 消耗")
        for session in MOCK_DEVICE_SESSIONS:
            call = tracker.record(
                session_id=session["session_id"],
                device_id=session["device_id"],
                input_text=session["input"],
                output_text=session["output"],
            )
            print(f"   {session['device_id']}: "
                  f"输入 {call.input_tokens} tokens, "
                  f"输出 {call.output_tokens} tokens, "
                  f"成本 ${call.cost_usd:.6f}")

        # ── Step 2: 全局统计摘要 ──────────────────────────────────────
        print("\n── Step 2: 全局统计摘要")
        summary = tracker.summary()
        for k, v in summary.items():
            print(f"   {k}: {v}")

        # ── Step 3: 月度成本估算 ──────────────────────────────────────
        print("\n── Step 3: 月度成本估算（假设每日处理 50 次告警）")
        estimate = tracker.monthly_estimate(daily_alarm_rate=50)
        print(f"   每次平均成本: ${estimate['avg_cost_per_call_usd']:.6f}")
        print(f"   月度预计调用: {estimate['monthly_calls_estimate']} 次")
        print(f"   月度预计成本: ${estimate['monthly_cost_usd']:.2f} USD")

        print(f"\n{'='*60}")
        print("演示完成。MOCK_MODE 下不依赖任何 AWS 资源。")
        print(f"注意：定价数据仅供参考，请以 AWS 官方定价页面为准。")
        print(f"{'='*60}\n")

    except Exception as exc:
        print(f"\n[ERROR] 演示运行失败: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
