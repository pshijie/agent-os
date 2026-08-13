# Module:   01-memory / Working Memory + Episodic Memory
# Ref:      hello-agents/code/chapter8/03_WorkingMemory_Implementation.py
# Scenario: 某储能企业设备实时告警上下文管理
# Deps:     boto3>=1.34 (optional, only needed when MOCK_MODE=false)
# Run:      MOCK_MODE=true python memory_demo.py

"""
某企业 设备告警上下文管理演示
====================================
演示工作记忆（WorkingMemory）和情景记忆（EpisodicMemory）的核心机制：
- WorkingMemory: 带 TTL 的内存字典，存储当前诊断会话的活跃上下文
- EpisodicMemory: 历史告警事件列表，支持简单相似度检索
在 MOCK_MODE=true 时不依赖任何外部 API 即可完整运行演示。
"""

from __future__ import annotations

import os
import sys
import time
import hashlib
from datetime import datetime, timezone
from typing import Any

# ── 配置 ─────────────────────────────────────────────────────────────
MOCK_MODE: bool = os.environ.get("MOCK_MODE", "false").lower() == "true"
WORKING_MEMORY_TTL: int = int(os.environ.get("WORKING_MEMORY_TTL", "1800"))   # 默认 30min
WORKING_MEMORY_CAPACITY: int = int(os.environ.get("WORKING_MEMORY_CAPACITY", "50"))
EPISODIC_MEMORY_MAX: int = int(os.environ.get("EPISODIC_MEMORY_MAX", "1000"))

# AWS 配置（仅 MOCK_MODE=false 时使用）
AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")
DYNAMODB_TABLE: str = os.environ.get("DYNAMODB_TABLE", "iot-agent-episodic-memory")


# ── WorkingMemory ────────────────────────────────────────────────────
class WorkingMemory:
    """
    工作记忆：带 TTL 的内存字典，模拟 Agent 当前会话的活跃上下文。
    类比：Redis EXPIRE / JVM ThreadLocal，容量有限，超时自动失效。
    """

    def __init__(self, ttl: int = WORKING_MEMORY_TTL, capacity: int = WORKING_MEMORY_CAPACITY):
        self._store: dict[str, dict[str, Any]] = {}
        self.ttl = ttl
        self.capacity = capacity

    def write(self, key: str, value: Any, importance: float = 0.5) -> None:
        """写入记忆条目，超容量时淘汰重要性最低的条目。"""
        self._evict_expired()
        # 容量超限：淘汰 importance 最低的条目
        if len(self._store) >= self.capacity:
            oldest_key = min(
                self._store,
                key=lambda k: self._store[k]["importance"]
            )
            del self._store[oldest_key]
        self._store[key] = {
            "value": value,
            "importance": importance,
            "expires_at": time.time() + self.ttl,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def read(self, key: str) -> Any | None:
        """读取记忆条目，过期返回 None 并自动清除。"""
        self._evict_expired()
        entry = self._store.get(key)
        return entry["value"] if entry else None

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [k for k, v in self._store.items() if v["expires_at"] < now]
        for k in expired:
            del self._store[k]

    def snapshot(self) -> dict[str, Any]:
        """返回当前所有未过期条目的快照（用于 GSSC Gather 阶段）。"""
        self._evict_expired()
        return {k: v["value"] for k, v in self._store.items()}

    def stats(self) -> dict[str, int]:
        self._evict_expired()
        return {"active_entries": len(self._store), "capacity": self.capacity}


# ── EpisodicMemory ───────────────────────────────────────────────────
class EpisodicMemory:
    """
    情景记忆：历史诊断事件列表，支持基于关键词的简单相似度检索。
    生产环境可替换为 DynamoDB + OpenSearch 向量检索。
    """

    def __init__(self, max_size: int = EPISODIC_MEMORY_MAX):
        self._events: list[dict[str, Any]] = []
        self.max_size = max_size

    def record(self, event: dict[str, Any]) -> str:
        """
        记录一条诊断事件，返回事件 ID。
        event 至少包含: device_id, fault_type, diagnosis_result, importance
        """
        if len(self._events) >= self.max_size:
            # 淘汰重要性最低的历史事件
            self._events.sort(key=lambda e: e.get("importance", 0.5))
            self._events.pop(0)
        event_id = hashlib.md5(
            f"{event.get('device_id')}{time.time()}".encode()
        ).hexdigest()[:8]
        event["event_id"] = event_id
        event["recorded_at"] = datetime.now(timezone.utc).isoformat()
        self._events.append(event)
        return event_id

    def search_similar(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        """
        关键词相似度检索（Mock 版本）。
        生产版本应使用 embedding 向量 + kNN 检索（Amazon OpenSearch / DynamoDB）。
        """
        if MOCK_MODE:
            return self._mock_search(query, top_k)
        # 真实实现：调用 Amazon OpenSearch 向量检索
        # client = boto3.client("opensearch", region_name=AWS_REGION)
        # ... (实现略，参考 AWS OpenSearch k-NN 文档)
        return self._mock_search(query, top_k)

    def _mock_search(self, query: str, top_k: int) -> list[dict[str, Any]]:
        """基于关键词重叠的简单相似度排序（演示用）。"""
        query_tokens = set(query.lower().split())
        scored = []
        for event in self._events:
            text = f"{event.get('fault_type','')} {event.get('diagnosis_result','')}".lower()
            overlap = len(query_tokens & set(text.split()))
            if overlap > 0:
                scored.append((overlap, event))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]]

    def stats(self) -> dict[str, int]:
        return {"total_events": len(self._events), "max_size": self.max_size}


# ── Mock 数据 ────────────────────────────────────────────────────────
MOCK_HISTORICAL_EVENTS = [
    {
        "device_id": "DEV-001",
        "fault_type": "over_temperature",
        "diagnosis_result": "传感器单元 温度异常前兆，降低充电电流至额定值 50%",
        "resolution": "降低充电电流后温度恢复正常，持续监控 2h",
        "importance": 0.92,
    },
    {
        "device_id": "DEV-038",
        "fault_type": "over_temperature",
        "diagnosis_result": "温控系统散热不足，建议检查冷却风扇",
        "resolution": "更换风扇后故障消除",
        "importance": 0.87,
    },
    {
        "device_id": "DEV-015",
        "fault_type": "under_voltage",
        "diagnosis_result": "电池组老化，容量衰减至 78%，建议更换",
        "resolution": "更换设备模块，系统恢复正常",
        "importance": 0.80,
    },
]


# ── main ─────────────────────────────────────────────────────────────
def main() -> None:
    mode_label = "[MOCK]" if MOCK_MODE else "[LIVE]"
    print(f"\n{'='*60}")
    print(f"某企业 设备告警上下文管理演示  {mode_label}")
    print(f"{'='*60}\n")

    try:
        wm = WorkingMemory()
        em = EpisodicMemory()

        # ── Step 1: 预填充历史案例 ───────────────────────────────────
        print("── Step 1: 写入历史诊断案例到情景记忆")
        for event in MOCK_HISTORICAL_EVENTS:
            eid = em.record(event.copy())
            print(f"   [{eid}] {event['device_id']} / {event['fault_type']}")
        print(f"   {em.stats()}\n")

        # ── Step 2: 新告警触发，写入工作记忆 ───────────────────────────
        print("── Step 2: DEV-042 过温告警触发，写入工作记忆")
        alarm_context = {
            "device_id": "DEV-042",
            "alarm_type": "over_temperature",
            "temperature_celsius": 68.5,
            "threshold_celsius": 60.0,
            "battery_model": "MODEL-A",
            "soc_percent": 82.3,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        wm.write("current_alarm", alarm_context, importance=0.95)
        wm.write("session_id", "diag-session-dev042", importance=1.0)
        print(f"   工作记忆快照: {wm.snapshot()}\n")

        # ── Step 3: 检索相似历史案例 ─────────────────────────────────
        print("── Step 3: 检索相似历史案例（Top-3）")
        query = "over_temperature 过温 设备组件"
        similar = em.search_similar(query, top_k=3)
        if similar:
            for i, case in enumerate(similar, 1):
                print(f"   [{i}] {case['device_id']}: {case['diagnosis_result']}")
        else:
            print("   未找到相似历史案例")
        print()

        # ── Step 4: 组装诊断上下文 ───────────────────────────────────
        print("── Step 4: 组装诊断上下文（工作记忆 + 历史案例）")
        diagnostic_context = {
            "current_alarm": wm.read("current_alarm"),
            "historical_cases": similar,
            "recommendation": (
                "[MOCK] 根据历史案例，建议降低充电电流至额定值 50% 并监控温度趋势。"
                if MOCK_MODE else "（此处调用 Amazon Bedrock 生成诊断建议）"
            ),
        }
        print(f"   设备: {diagnostic_context['current_alarm']['device_id']}")
        print(f"   告警: {diagnostic_context['current_alarm']['alarm_type']}")
        print(f"   温度: {diagnostic_context['current_alarm']['temperature_celsius']}°C")
        print(f"   诊断: {diagnostic_context['recommendation']}\n")

        # ── Step 5: 将本次诊断写回情景记忆 ──────────────────────────
        print("── Step 5: 本次诊断写回情景记忆")
        new_event = {
            "device_id": "DEV-042",
            "fault_type": "over_temperature",
            "diagnosis_result": diagnostic_context["recommendation"],
            "resolution": "降低充电电流后持续监控",
            "importance": 0.90,
        }
        new_eid = em.record(new_event)
        print(f"   已记录事件 [{new_eid}]")
        print(f"   {em.stats()}\n")

        print(f"{'='*60}")
        print("演示完成。MOCK_MODE 下无需任何 AWS 凭证。")
        print(f"{'='*60}\n")

    except Exception as exc:
        print(f"\n[ERROR] 演示运行失败: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
