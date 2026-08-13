# Module:   03-planning / ReAct Agent
# Ref:      hello-agents/code/chapter4/ReAct.py
# Scenario: 某储能企业设备故障诊断推理链（ReAct 范式）
# Deps:     (MOCK_MODE=true 时无外部依赖)  boto3>=1.34 (optional)
# Run:      MOCK_MODE=true python react_agent.py

"""
某企业 设备故障诊断 ReAct Agent 演示
==========================================
演示 ReAct 范式的 Think → Act → Observe 循环：
- ReActAgent: 主推理循环，交织思考与工具调用
- ToolRegistry: 工具注册表（设备状态查询、手册检索）
- MockLLM: Mock LLM 响应（MOCK_MODE=true 时用于演示）
在 MOCK_MODE=true 时不依赖任何外部 API 即可完整运行演示。
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from typing import Callable, Any

# ── 配置 ─────────────────────────────────────────────────────────────
MOCK_MODE: bool = os.environ.get("MOCK_MODE", "false").lower() == "true"
MAX_STEPS: int = int(os.environ.get("MAX_STEPS", "10"))

# AWS 配置（仅 MOCK_MODE=false 时使用）
AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")
BEDROCK_AGENT_ID: str = os.environ.get("BEDROCK_AGENT_ID", "")
BEDROCK_MODEL_ID: str = os.environ.get(
    "BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"
)


# ── 工具注册表 ────────────────────────────────────────────────────────
@dataclass
class Tool:
    name: str
    description: str
    func: Callable[[str], str]


class ToolRegistry:
    """工具注册表，类比 HelloAgents ToolExecutor"""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, name: str, description: str, func: Callable[[str], str]) -> None:
        self._tools[name] = Tool(name=name, description=description, func=func)

    def call(self, name: str, input_str: str) -> str:
        if name not in self._tools:
            return f"[错误] 工具 '{name}' 未注册。可用工具: {list(self._tools.keys())}"
        try:
            return self._tools[name].func(input_str)
        except Exception as exc:
            return f"[错误] 工具 '{name}' 执行失败: {exc}"

    def descriptions(self) -> str:
        return "\n".join(
            f"  - {t.name}: {t.description}" for t in self._tools.values()
        )


# ── Mock 工具实现 ─────────────────────────────────────────────────────
def mock_query_device_status(device_id: str) -> str:
    """Mock: 查询设备实时状态"""
    devices = {
        "DEV-042": {
            "temperature": 68.5, "threshold": 60.0,
            "voltage": 52.3, "current": -12.5,
            "soc": 82.3, "status": "ALARM",
            "alarm_code": "DEV-042-OVERTEMP",
        },
        "DEV-001": {
            "temperature": 35.2, "threshold": 60.0,
            "voltage": 53.1, "current": 8.0,
            "soc": 75.0, "status": "NORMAL",
        },
    }
    data = devices.get(device_id.strip().upper(), {"error": "设备不存在"})
    lines = [f"{k}: {v}" for k, v in data.items()]
    return "设备状态:\n" + "\n".join(f"  {l}" for l in lines)


def mock_search_manual(query: str) -> str:
    """Mock: 检索设备手册"""
    manual_db = {
        "过温": (
            "§4.2 设备温度保护规程\n"
            "一级保护（60–75°C）：降低充电电流至额定值 50%，启动强制散热风扇（100%）。\n"
            "二级保护（≥75°C）：触发保护性断电，立即联系技术支持。"
        ),
        "欠压": (
            "§3.4.7 单体电池欠压保护（E047）\n"
            "触发条件：单体电压 < 欠压阈值 持续 5 秒。\n"
            "处置：检查采样线，执行均衡充电程序（§6.3）。"
        ),
        "充电": (
            "§5.3 充电参数规格（MODEL-A）\n"
            "标准充电电流: 额定值；快充上限: 额定值 150%（15–35°C，≤2h）\n"
            "充电截止电压: 额定截止电压/单体；截止温度: 45°C。"
        ),
    }
    for keyword, content in manual_db.items():
        if keyword in query:
            return f"手册检索结果（关键词: {keyword}）:\n{content}"
    return f"手册检索结果: 未找到与 '{query}' 直接相关的规程，建议查阅第 3–6 章。"


# ── Mock LLM ──────────────────────────────────────────────────────────
class MockLLM:
    """
    Mock LLM：根据对话历史返回预定义的 ReAct 格式响应。
    生产版替换为 boto3.client('bedrock-runtime').invoke_model()。
    """

    def __init__(self) -> None:
        # 预定义多步推理脚本
        self._script: list[str] = [
            (
                "Thought: 收到 DEV-042 过温告警，首先查询设备当前实时状态，确认告警真实性。\n"
                "Action: query_device_status[DEV-042]"
            ),
            (
                "Thought: 温度 68.5°C 已超阈值 60°C，告警属实。"
                "需要查阅设备手册的过温处置规程。\n"
                "Action: search_manual[设备过温处置规程]"
            ),
            (
                "Thought: 规程明确：一级保护应降低充电电流至额定值 50% 并启动强制散热。"
                "当前温度 68.5°C 未触及 75°C 断电阈值，执行一级处置。\n"
                "Action: Finish[【诊断结论】DEV-042 设备过温（68.5°C，阈值 60°C）。"
                "建议：① 立即降低充电电流至额定值 50%；② 启动强制散热风扇（100% 风速）；"
                "③ 持续监控温度，若 5 分钟内未降温且超过 75°C，触发保护性断电。"
                "依据：§4.2 设备温度保护规程。]"
            ),
        ]
        self._step = 0

    def generate(self, prompt: str) -> str:  # noqa: ARG002
        if self._step < len(self._script):
            resp = self._script[self._step]
            self._step += 1
            return resp
        return "Action: Finish[已完成所有推理步骤，无更多行动。]"


# ── ReActAgent ────────────────────────────────────────────────────────
class ReActAgent:
    """
    ReAct Agent：交织推理（Think）与行动（Act）的单步循环智能体。
    对应 Amazon Bedrock Agents 内置的 ReAct 编排（orchestrationType: DEFAULT）。
    """

    def __init__(
        self,
        tools: ToolRegistry,
        max_steps: int = MAX_STEPS,
    ) -> None:
        self.tools = tools
        self.max_steps = max_steps       # Circuit Breaker：防止无限循环
        self._llm = MockLLM() if MOCK_MODE else None

    def run(self, task: str) -> str:
        """主循环：反复执行 Think → Act → Observe，直到 Finish 或超步"""
        history: list[tuple[str, str, str]] = []   # (thought, action, observation)

        print(f"\n   任务: {task}")
        for step in range(1, self.max_steps + 1):
            print(f"\n   ── Step {step} ──")

            # Think：生成 Thought + Action
            raw = self._think(task, history)
            thought, action_str = self._parse_output(raw)
            if thought:
                print(f"   Thought: {thought[:120]}...")

            if not action_str:
                print("   [警告] 未解析到有效 Action，终止循环")
                break

            action_name, action_input = self._parse_action(action_str)

            # 识别 Finish 信号
            if action_name == "Finish":
                print(f"   Action: Finish[...]")
                final = action_input
                print(f"\n   [OK] 最终结论: {final[:300]}")
                return final

            print(f"   Action: {action_name}[{action_input[:60]}]")

            # Act：调用工具
            observation = self.tools.call(action_name, action_input)
            print(f"   Observe: {observation[:120]}...")

            # 记录轨迹
            history.append((thought, action_str, observation))

        return f"[超步] 已达最大步数 {self.max_steps}，最后观察: {history[-1][2] if history else '无'}"

    def _think(self, task: str, history: list) -> str:
        """调用 LLM 生成 Thought + Action"""
        if MOCK_MODE and self._llm:
            return self._llm.generate(task)
        # 真实 Amazon Bedrock 调用（略）
        # import boto3
        # client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        # ...
        raise RuntimeError("MOCK_MODE=false 但未配置 Bedrock 客户端，请设置 MOCK_MODE=true 或配置 AWS 环境变量。")

    @staticmethod
    def _parse_output(raw: str) -> tuple[str, str]:
        """从 LLM 输出中提取 Thought 和 Action"""
        thought_m = re.search(r"Thought:\s*(.*?)(?=\nAction:|$)", raw, re.DOTALL)
        action_m = re.search(r"Action:\s*(.*?)$", raw, re.DOTALL)
        return (
            thought_m.group(1).strip() if thought_m else "",
            action_m.group(1).strip() if action_m else "",
        )

    @staticmethod
    def _parse_action(action_str: str) -> tuple[str, str]:
        """解析 'ToolName[input]' 格式"""
        m = re.match(r"(\w+)\[(.+)\]", action_str, re.DOTALL)
        if m:
            return m.group(1), m.group(2)
        return action_str, ""


# ── main ──────────────────────────────────────────────────────────────
def main() -> None:
    mode_label = "[MOCK]" if MOCK_MODE else "[LIVE]"
    print(f"\n{'='*60}")
    print(f"某企业 设备故障诊断 ReAct Agent 演示  {mode_label}")
    print(f"{'='*60}")

    try:
        # 注册诊断工具
        registry = ToolRegistry()
        registry.register(
            "query_device_status",
            "查询 IoT 设备的实时传感器状态（温度、电压、电流、SOC、告警码）",
            mock_query_device_status,
        )
        registry.register(
            "search_manual",
            "检索 某企业 设备手册中的处置规程（支持关键词：过温、欠压、充电等）",
            mock_search_manual,
        )

        # 创建 ReAct Agent
        agent = ReActAgent(tools=registry, max_steps=MAX_STEPS)

        # 演示：DEV-042 过温告警诊断
        task = "DEV-042 设备上报过温告警，请诊断原因并给出处置建议。"
        result = agent.run(task)

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
