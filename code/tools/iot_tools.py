# Module:   04-action-tools / IoT Diagnostic Tools
# Ref:      hello-agents/code/chapter7/tools
# Scenario: 某储能企业设备诊断工具集（设备状态查询 + 告警历史检索）
# Deps:     (MOCK_MODE=true 时无外部依赖)  boto3>=1.34 (optional)
# Run:      MOCK_MODE=true python iot_tools.py

"""
IoT 企业 诊断工具演示
============================
实现统一工具接口 tool.run(input: dict) -> dict：
- DeviceStatusTool:  查询设备实时传感器状态
- AlarmHistoryTool:  检索设备历史告警记录
在 MOCK_MODE=true 时使用内置 fixture 数据，无需真实 IoT 后端。
"""

from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

# ── 配置 ─────────────────────────────────────────────────────────────
MOCK_MODE: bool = os.environ.get("MOCK_MODE", "false").lower() == "true"
IOT_ENDPOINT: str = os.environ.get("IOT_ENDPOINT", "https://iot.amazonaws.com")
AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")


# ── 统一工具接口 ──────────────────────────────────────────────────────
class BaseTool(ABC):
    """
    统一工具接口：tool.run(input: dict) -> dict
    对应 HelloAgents 的 "Everything is a Tool" 设计哲学。
    生产版对应 Amazon Bedrock AgentCore Action Groups。
    """
    name: str
    description: str

    @abstractmethod
    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """执行工具，返回结构化结果"""
        ...


# ── Mock 数据 ─────────────────────────────────────────────────────────
MOCK_DEVICE_DB: dict[str, dict[str, Any]] = {
    "DEV-042": {
        "device_id": "DEV-042", "model": "MODEL-A",
        "temperature": 68.5, "threshold": 60.0,
        "voltage": 52.3, "current": -12.5,
        "soc": 82.3, "status": "ALARM",
        "alarm_code": "OVER_TEMP",
        "last_updated": "2025-01-28T10:23:45Z",
    },
    "DEV-001": {
        "device_id": "DEV-001", "model": "MODEL-A",
        "temperature": 34.1, "threshold": 60.0,
        "voltage": 53.1, "current": 8.0,
        "soc": 75.0, "status": "NORMAL",
        "alarm_code": None,
        "last_updated": "2025-01-28T10:23:44Z",
    },
    "DEV-038": {
        "device_id": "DEV-038", "model": "MODEL-B",
        "temperature": 41.2, "threshold": 55.0,
        "voltage": 51.8, "current": 5.5,
        "soc": 60.3, "status": "NORMAL",
        "alarm_code": None,
        "last_updated": "2025-01-28T10:23:43Z",
    },
}

MOCK_ALARM_HISTORY: dict[str, list[dict[str, Any]]] = {
    "DEV-042": [
        {
            "alarm_id": "ALM-20250110-001", "device_id": "DEV-042",
            "alarm_type": "OVER_TEMP", "temperature": 65.2,
            "timestamp": "2025-01-10T14:22:00Z",
            "resolution": "降低充电电流至额定值 50%，30 分钟后温度恢复正常",
            "severity": "LEVEL_2",
        },
        {
            "alarm_id": "ALM-20241205-007", "device_id": "DEV-042",
            "alarm_type": "OVER_TEMP", "temperature": 62.1,
            "timestamp": "2024-12-05T09:15:00Z",
            "resolution": "散热风扇启动，15 分钟后恢复",
            "severity": "LEVEL_1",
        },
    ],
    "DEV-038": [
        {
            "alarm_id": "ALM-20241130-003", "device_id": "DEV-038",
            "alarm_type": "FAN_FAILURE", "temperature": 58.7,
            "timestamp": "2024-11-30T16:40:00Z",
            "resolution": "更换散热风扇，故障消除",
            "severity": "LEVEL_3",
        },
    ],
}


# ── DeviceStatusTool ──────────────────────────────────────────────────
class DeviceStatusTool(BaseTool):
    """
    查询设备实时传感器状态。
    生产版对应 AWS IoT Core 设备影子 API（GetThingShadow）。
    """
    name = "device_status"
    description = "查询 IoT 设备的实时传感器状态（温度、电压、电流、SOC、告警码）"

    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        device_id = str(input_data.get("device_id", "")).strip().upper()
        if not device_id:
            return {"error": "缺少必填参数 device_id"}

        if MOCK_MODE:
            return self._mock_run(device_id)
        return self._aws_run(device_id)

    def _mock_run(self, device_id: str) -> dict[str, Any]:
        data = MOCK_DEVICE_DB.get(device_id)
        if not data:
            return {"error": f"设备 {device_id} 不存在（Mock 库中有: {list(MOCK_DEVICE_DB.keys())}）"}
        return {"status": "ok", "data": data}

    def _aws_run(self, device_id: str) -> dict[str, Any]:
        try:
            import boto3  # type: ignore
            client = boto3.client("iot-data", region_name=AWS_REGION)
            resp = client.get_thing_shadow(thingName=device_id)
            import json
            payload = json.loads(resp["payload"].read())
            return {"status": "ok", "data": payload.get("state", {}).get("reported", {})}
        except Exception as exc:
            return {"error": f"AWS IoT 查询失败: {exc}"}


# ── AlarmHistoryTool ──────────────────────────────────────────────────
class AlarmHistoryTool(BaseTool):
    """
    检索设备历史告警记录。
    生产版对应 Amazon DynamoDB 查询（按 device_id GSI 检索）。
    """
    name = "alarm_history"
    description = "检索设备的历史告警记录，支持按设备 ID 和告警类型过滤，返回最近 N 条"

    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        device_id = str(input_data.get("device_id", "")).strip().upper()
        alarm_type = input_data.get("alarm_type")       # 可选过滤
        limit = int(input_data.get("limit", 5))

        if not device_id:
            return {"error": "缺少必填参数 device_id"}

        if MOCK_MODE:
            return self._mock_run(device_id, alarm_type, limit)
        return self._aws_run(device_id, alarm_type, limit)

    def _mock_run(
        self, device_id: str, alarm_type: str | None, limit: int
    ) -> dict[str, Any]:
        records = MOCK_ALARM_HISTORY.get(device_id, [])
        if alarm_type:
            records = [r for r in records if r.get("alarm_type") == alarm_type.upper()]
        records = sorted(records, key=lambda r: r["timestamp"], reverse=True)[:limit]
        return {
            "status": "ok",
            "device_id": device_id,
            "total": len(records),
            "records": records,
        }

    def _aws_run(self, device_id: str, alarm_type: str | None, limit: int) -> dict[str, Any]:
        try:
            import boto3  # type: ignore
            dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
            table = dynamodb.Table(os.environ.get("ALARM_TABLE", "iot-agent-alarms"))
            kwargs: dict[str, Any] = {
                "IndexName": "DeviceIdIndex",
                "KeyConditionExpression": "device_id = :did",
                "ExpressionAttributeValues": {":did": device_id},
                "Limit": limit,
                "ScanIndexForward": False,
            }
            if alarm_type:
                kwargs["FilterExpression"] = "alarm_type = :at"
                kwargs["ExpressionAttributeValues"][":at"] = alarm_type.upper()
            resp = table.query(**kwargs)
            return {"status": "ok", "device_id": device_id,
                    "total": resp.get("Count", 0), "records": resp.get("Items", [])}
        except Exception as exc:
            return {"error": f"DynamoDB 查询失败: {exc}"}


# ── main ──────────────────────────────────────────────────────────────
def main() -> None:
    mode_label = "[MOCK]" if MOCK_MODE else "[LIVE]"
    print(f"\n{'='*60}")
    print(f"IoT 企业 诊断工具演示  {mode_label}")
    print(f"{'='*60}\n")

    try:
        device_tool = DeviceStatusTool()
        alarm_tool = AlarmHistoryTool()

        # ── 演示 1: 查询 DEV-042 实时状态 ────────────────────────────
        print("── 演示 1: 查询 DEV-042 实时状态")
        result = device_tool.run({"device_id": "DEV-042"})
        if result.get("status") == "ok":
            data = result["data"]
            print(f"   设备: {data['device_id']}  状态: {data['status']}")
            print(f"   温度: {data['temperature']}°C / 阈值 {data['threshold']}°C")
            print(f"   SOC:  {data['soc']}%  告警码: {data.get('alarm_code', '无')}")
        else:
            print(f"   错误: {result.get('error')}")

        # ── 演示 2: 查询正常设备 ──────────────────────────────────────
        print("\n── 演示 2: 查询 DEV-001 实时状态（正常设备）")
        result2 = device_tool.run({"device_id": "DEV-001"})
        data2 = result2.get("data", {})
        print(f"   设备: {data2.get('device_id')}  状态: {data2.get('status')}")
        print(f"   温度: {data2.get('temperature')}°C  SOC: {data2.get('soc')}%")

        # ── 演示 3: 检索 DEV-042 历史告警 ────────────────────────────
        print("\n── 演示 3: 检索 DEV-042 历史过温告警（Top-3）")
        hist = alarm_tool.run({"device_id": "DEV-042", "alarm_type": "OVER_TEMP", "limit": 3})
        records = hist.get("records", [])
        print(f"   共找到 {hist.get('total', 0)} 条历史告警")
        for r in records:
            print(f"   [{r['timestamp']}] {r['alarm_type']} - {r.get('resolution', '无')}")

        # ── 演示 4: 查询不存在的设备（错误处理） ─────────────────────
        print("\n── 演示 4: 查询不存在的设备（错误处理验证）")
        err_result = device_tool.run({"device_id": "DEV-xxx"})
        print(f"   错误响应: {err_result.get('error')}")

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
