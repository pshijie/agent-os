# Module:   10-multi-agent / Orchestrator + Worker Demo
# Ref:      hello-agents/code/chapter13-15/multi_agent
# Scenario: 某企业 多 Agent 协作：协调器 + 执行器故障诊断演示
# Deps:     (MOCK_MODE=true 时无外部依赖)
# Run:      MOCK_MODE=true python orchestrator_demo.py

"""
某企业 多 Agent 协作演示
================================
演示 Orchestrator-Worker 架构：
- OrchestratorAgent:  接收故障诊断请求，分解为子任务，分发给 Worker Agent
- WorkerAgent:        执行具体子任务（温度分析、规程检索、报告生成）
- AgentMessage:       Agent 间标准化消息格式
在 MOCK_MODE=true 时使用预定义脚本，无需真实 LLM 调用。
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# ── 配置 ─────────────────────────────────────────────────────────────
MOCK_MODE: bool = os.environ.get("MOCK_MODE", "false").lower() == "true"
MAX_WORKERS: int = int(os.environ.get("MAX_WORKERS", "3"))


# ── Agent 消息格式 ────────────────────────────────────────────────────
@dataclass
class AgentMessage:
    """Agent 间通信消息（对应 A2A Protocol 消息格式）"""
    sender: str
    receiver: str
    task: str
    payload: dict[str, Any] = field(default_factory=dict)
    message_id: str = field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    )


@dataclass
class AgentResult:
    """Worker Agent 执行结果"""
    worker_id: str
    task: str
    result: str
    success: bool
    tokens_used: int = 0


# ── Worker Agent ──────────────────────────────────────────────────────
class WorkerAgent:
    """
    执行器 Agent：接收子任务并返回结果。
    对应 Amazon Bedrock AgentCore Sub-Agent。
    """

    def __init__(self, worker_id: str, specialization: str) -> None:
        self.worker_id = worker_id
        self.specialization = specialization  # 专业领域（温度分析/规程检索/报告生成）
        self._mock_responses: dict[str, str] = {
            "analyze_temperature": (
                "温度分析结论：DEV-042 当前温度 68.5°C，超过一级保护阈值 60°C。"
                "温度趋势：过去 10 分钟上升 2.1°C/min，属于持续上升型过温。"
                "风险评分：0.72（高风险，但未达二级保护阈值 75°C）。"
            ),
            "retrieve_procedure": (
                "处置规程检索结果（§4.2 设备温度保护规程）："
                "一级保护措施：① 降低充电电流至额定值 50%；② 启动强制散热风扇（100%风速）。"
                "复位条件：温度降至 55°C 以下后，可解除保护并恢复正常充电。"
            ),
            "generate_report": (
                "【某企业 设备诊断报告】\n"
                "设备：DEV-042  时间：2025-01-28T10:30:00Z\n"
                "故障类型：设备过温（Level-2 告警）\n"
                "诊断结论：设备组件温度 68.5°C 超阈值，建议执行一级保护措施。\n"
                "行动项：① 立即降低充电电流至额定值 50%；② 启动散热风扇；"
                "③ 5分钟内重新检查温度。若超过 75°C，触发保护性断电。"
            ),
        }

    def execute(self, message: AgentMessage) -> AgentResult:
        """执行子任务，返回结果"""
        task_key = message.task.lower().replace(" ", "_").replace("/", "_")
        # 找到最匹配的 mock 响应
        for key in self._mock_responses:
            if key in task_key:
                return AgentResult(
                    worker_id=self.worker_id,
                    task=message.task,
                    result=self._mock_responses[key],
                    success=True,
                    tokens_used=200 + len(self._mock_responses[key]) // 4,
                )
        return AgentResult(
            worker_id=self.worker_id,
            task=message.task,
            result=f"[{self.specialization}] 已完成任务：{message.task}",
            success=True,
            tokens_used=150,
        )


# ── Orchestrator Agent ────────────────────────────────────────────────
class OrchestratorAgent:
    """
    协调器 Agent：分解任务、分发给 Worker、聚合结果。
    对应 Amazon Bedrock AgentCore Supervisor Agent。
    """

    def __init__(self, workers: list[WorkerAgent]) -> None:
        self._workers = {w.worker_id: w for w in workers}
        self._worker_list = workers

    def _decompose_task(self, diagnosis_request: str) -> list[dict[str, Any]]:
        """将诊断请求分解为子任务列表（Mock 版：固定分解逻辑）"""
        return [
            {"task": "analyze_temperature", "worker": "temperature-analyst",
             "payload": {"device_id": "DEV-042"}},
            {"task": "retrieve_procedure", "worker": "knowledge-retriever",
             "payload": {"alarm_type": "OVER_TEMP"}},
            {"task": "generate_report", "worker": "report-generator",
             "payload": {"device_id": "DEV-042", "level": 2}},
        ]

    def run(self, diagnosis_request: str) -> dict[str, Any]:
        """
        主流程：分解任务 → 顺序分发给 Worker → 聚合结果。
        生产版可替换为并发分发（asyncio 或 threading）。
        """
        print(f"\n   [Orchestrator] 收到诊断请求: {diagnosis_request}")

        # 1. 任务分解
        subtasks = self._decompose_task(diagnosis_request)
        print(f"   [Orchestrator] 分解为 {len(subtasks)} 个子任务")

        # 2. 顺序分发并收集结果
        results: list[AgentResult] = []
        for i, subtask in enumerate(subtasks, 1):
            worker_id = subtask["worker"]
            worker = self._workers.get(worker_id)
            if not worker:
                print(f"   [Orchestrator] 警告: Worker '{worker_id}' 不存在，跳过")
                continue

            msg = AgentMessage(
                sender="orchestrator",
                receiver=worker_id,
                task=subtask["task"],
                payload=subtask["payload"],
            )
            print(f"\n   [Orchestrator -> {worker_id}] 分发子任务: {subtask['task']}")
            result = worker.execute(msg)
            results.append(result)

            status = "[OK]" if result.success else "[FAIL]"
            print(f"   [{worker_id} -> Orchestrator] {status} 完成 ({result.tokens_used} tokens)")
            print(f"   结果摘要: {result.result[:120]}...")

        # 3. 聚合最终报告
        total_tokens = sum(r.tokens_used for r in results)
        success_count = sum(1 for r in results if r.success)

        return {
            "diagnosis_request": diagnosis_request,
            "subtasks_total": len(subtasks),
            "subtasks_completed": success_count,
            "total_tokens_used": total_tokens,
            "final_report": next(
                (r.result for r in results if "report" in r.task.lower()), "报告生成失败"
            ),
            "all_results": [{"task": r.task, "result": r.result} for r in results],
        }


# ── main ──────────────────────────────────────────────────────────────
def main() -> None:
    mode_label = "[MOCK]" if MOCK_MODE else "[LIVE]"
    print(f"\n{'='*60}")
    print(f"某企业 多 Agent 协作演示  {mode_label}")
    print(f"{'='*60}")

    try:
        # 初始化 Worker Agent 池
        workers = [
            WorkerAgent("temperature-analyst", "设备温度分析"),
            WorkerAgent("knowledge-retriever", "设备手册知识库检索"),
            WorkerAgent("report-generator", "诊断报告生成"),
        ]
        orchestrator = OrchestratorAgent(workers)

        # 运行故障诊断
        request = "DEV-042 发生过温告警（68.5°C），请进行完整故障诊断。"
        output = orchestrator.run(request)

        print(f"\n── 汇总结果")
        print(f"   子任务完成: {output['subtasks_completed']}/{output['subtasks_total']}")
        print(f"   总 Token 消耗: {output['total_tokens_used']}")
        print(f"\n── 最终诊断报告")
        print(output["final_report"])

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
