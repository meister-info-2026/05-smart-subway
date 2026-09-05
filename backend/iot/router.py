"""
FastAPI Router for IoT Device Control, Vision Events, and Sensor Ingestion.
Follows api-rules.md and iot-endpoint-generator skill specifications.
"""

import datetime
import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, status
from iot.provider_factory import get_device_provider
from schemas.device import (
    DeviceControlRequest,
    PressureSimulateRequest,
    VisionEventCreate,
)
from websocket_manager import ws_manager

logger = logging.getLogger("backend.iot.router")

router = APIRouter(prefix="/api/v1", tags=["IoT & Vision"])

# 환경 변수에서 디바이스 API 키 가져오기
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "your_secret_device_api_key_here")

# 최근 영상 감지 이벤트 메모리 버퍼 (DB 부재 시에도 대시보드 피드 즉시 제공)
_recent_vision_events: List[Dict[str, Any]] = []


def verify_device_api_key(x_device_api_key: Optional[str] = Header(None)) -> bool:
    """디바이스향 엔드포인트(라즈베리파이, Vision 클라이언트)의 API 키를 검증합니다."""
    if not x_device_api_key or x_device_api_key != DEVICE_API_KEY:
        # 보안 규칙: 불일치 시 401 Unauthorized
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Invalid or missing X-Device-Api-Key"}},
        )
    return True


# ------------------------------------------------------------------------------
# 1. 디바이스 조회 및 제어 API
# ------------------------------------------------------------------------------
@router.get("/devices")
async def get_all_devices() -> Dict[str, Any]:
    """등록된 모든 디바이스의 최신 상태 목록을 반환합니다."""
    provider = get_device_provider()
    devices = await provider.get_all_statuses()
    return {"data": devices}


@router.get("/devices/{device_id}")
async def get_device(device_id: str) -> Dict[str, Any]:
    """특정 디바이스의 상태를 반환합니다."""
    provider = get_device_provider()
    dev = await provider.get_device_status(device_id)
    if not dev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "DEVICE_NOT_FOUND", "message": f"Device '{device_id}' does not exist."}},
        )
    return {"data": dev}


@router.post("/devices/{device_id}/control")
async def control_device(device_id: str, req: DeviceControlRequest) -> Dict[str, Any]:
    """
    대시보드(사용자)에서 액추에이터의 상태를 제어합니다.
    """
    provider = get_device_provider()
    try:
        updated_device = await provider.set_actuator_state(
            device_id=device_id,
            desired_state=req.desired_state,
            value=req.desired_value,
            operator=req.operator,
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "DEVICE_NOT_FOUND", "message": f"Device '{device_id}' not found."}},
        )

    # WebSocket으로 전체 클라이언트에 실시간 브로드캐스트
    await ws_manager.broadcast({
        "type": "device_updated",
        "device": updated_device,
        "timestamp": datetime.datetime.now().isoformat(),
    })

    return {"data": updated_device}


@router.get("/devices/{device_id}/desired-state")
async def get_desired_state(device_id: str) -> Dict[str, Any]:
    """라즈베리파이 폴링용 엔드포인트: 목표 상태를 조회합니다."""
    provider = get_device_provider()
    dev = await provider.get_device_status(device_id)
    if not dev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "DEVICE_NOT_FOUND", "message": f"Device '{device_id}' not found."}},
        )
    return {
        "data": {
            "id": dev["id"],
            "desired_state": dev.get("desired_state"),
            "desired_value": dev.get("desired_value"),
        }
    }


@router.post("/devices/{device_id}/state")
async def report_device_state(
    device_id: str,
    payload: Dict[str, Any],
    x_device_api_key: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """라즈베리파이 상태 보고용 엔드포인트: 실제 반영된 현재 상태를 수신합니다."""
    verify_device_api_key(x_device_api_key)
    provider = get_device_provider()

    current_state = payload.get("current_state")
    current_value = payload.get("current_value")

    # Mock provider 또는 Hardware provider에 반영
    dev = await provider.get_device_status(device_id)
    if not dev:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "DEVICE_NOT_FOUND", "message": f"Device '{device_id}' not found."}},
        )

    dev["current_state"] = current_state
    if current_value is not None:
        dev["current_value"] = current_value
    dev["updated_at"] = datetime.datetime.now().isoformat()

    await ws_manager.broadcast({
        "type": "device_state_reported",
        "device": dev,
        "timestamp": datetime.datetime.now().isoformat(),
    })

    return {"data": dev}


# ------------------------------------------------------------------------------
# 2. 임산부석 압력센서 시뮬레이션 API
# ------------------------------------------------------------------------------
@router.post("/devices/sensor/pressure-simulate")
async def simulate_pressure_seat(req: PressureSimulateRequest) -> Dict[str, Any]:
    """
    대시보드에서 임산부석 압력센서의 착석/기립 상태를 시뮬레이션합니다.
    """
    provider = get_device_provider()
    if hasattr(provider, "simulate_pressure_seat"):
        dev = await provider.simulate_pressure_seat(occupied=req.occupied, pressure_val=req.pressure_val)
    else:
        dev = await provider.get_device_status("sensor_seat_pressure")
        if dev:
            dev["current_state"] = "occupied" if req.occupied else "empty"
            dev["current_value"] = {
                "occupied": req.occupied,
                "pressure_val": req.pressure_val if req.pressure_val is not None else (70.0 if req.occupied else 0.0),
            }

    # WebSocket 브로드캐스트
    await ws_manager.broadcast({
        "type": "pressure_seat_updated",
        "occupied": req.occupied,
        "device": dev,
        "timestamp": datetime.datetime.now().isoformat(),
    })

    return {"data": dev}


# ------------------------------------------------------------------------------
# 3. Vision 감지 이벤트 및 혼잡도 트리거 API
# ------------------------------------------------------------------------------
@router.post("/vision/events")
async def receive_vision_event(
    event: VisionEventCreate,
    x_device_api_key: Optional[str] = Header(None),
) -> Dict[str, Any]:
    """
    YOLO 영상인식 클라이언트로부터 사람 수 감지 이벤트를 수신하고,
    AGENTS.md 트리거 규칙에 따라 혼잡도를 판별하여 LED 목표 상태를 자동 갱신합니다.
    """
    verify_device_api_key(x_device_api_key)

    # 1. 트리거 규칙 적용 (혼잡도 레벨 및 LED 색상 결정)
    count = event.count
    if count <= 2:
        congestion_level = "여유"
        led_color = "GREEN"
    elif 3 <= count <= 5:
        congestion_level = "보통"
        led_color = "ORANGE"
    else:
        congestion_level = "혼잡"
        led_color = "RED"

    # 2. 디바이스 프로바이더 갱신 (카메라 & 혼잡도 LED)
    provider = get_device_provider()
    if hasattr(provider, "update_vision_metrics"):
        await provider.update_vision_metrics(
            person_count=count,
            congestion=congestion_level,
            led_color=led_color,
        )
    else:
        await provider.set_actuator_state(
            device_id="led_congestion",
            desired_state="on",
            value={"color": led_color, "level": congestion_level, "brightness": 100},
            operator="system",
        )

    # 3. DB 기록 (안전 처리)
    try:
        from db.database import log_vision_event
        log_vision_event(
            event_type=event.event_type,
            detected=event.detected,
            count=count,
            confidence=event.confidence,
        )
    except Exception as db_exc:
        logger.debug(f"DB vision event insert skipped: {db_exc}")

    # 4. 최근 이벤트 메모리 버퍼 저장 (최대 50개 유지)
    event_entry = {
        "event_type": event.event_type,
        "detected": event.detected,
        "count": count,
        "confidence": event.confidence,
        "congestion_level": congestion_level,
        "led_color": led_color,
        "created_at": datetime.datetime.now().isoformat(),
    }
    _recent_vision_events.insert(0, event_entry)
    if len(_recent_vision_events) > 50:
        _recent_vision_events.pop()

    # 5. WebSocket 브로드캐스트 (대시보드 실시간 반응)
    await ws_manager.broadcast({
        "type": "vision_event",
        "event": event_entry,
        "congestion_level": congestion_level,
        "led_color": led_color,
        "person_count": count,
        "timestamp": datetime.datetime.now().isoformat(),
    })

    return {"data": event_entry}


@router.get("/vision/events")
async def get_recent_vision_events(limit: int = 20) -> Dict[str, Any]:
    """최근 영상 감지 이벤트 목록을 반환합니다 (대시보드 피드용)."""
    return {"data": _recent_vision_events[:limit]}


# ------------------------------------------------------------------------------
# 4. 센서 히스토리 및 지하철 종합 현황 API (PRD 명세)
# ------------------------------------------------------------------------------
@router.get("/sensors/{device_id}/history")
async def get_sensor_history_endpoint(device_id: str, limit: int = 20) -> Dict[str, Any]:
    """특정 센서의 최근 측정 이력을 조회합니다."""
    try:
        from db.database import get_sensor_history
        history = get_sensor_history(device_id, limit=limit)
        return {"data": history}
    except Exception:
        # DB 연결이 안 된 경우 Mock 단일 최신값 반환
        provider = get_device_provider()
        dev = await provider.get_device_status(device_id)
        return {"data": [dev] if dev else []}


@router.get("/train/status")
async def get_train_status() -> Dict[str, Any]:
    """
    지하철 객차 종합 상태 정보를 반환합니다 (1호차/2호차 시각화용).
    """
    provider = get_device_provider()
    cam = await provider.get_device_status("cam_subway")
    led = await provider.get_device_status("led_congestion")
    pressure = await provider.get_device_status("sensor_seat_pressure")
    conveyor = await provider.get_device_status("motor_conveyor")

    person_count = 0
    congestion_level = "여유"
    led_color = "GREEN"
    if cam and "current_value" in cam:
        person_count = cam["current_value"].get("person_count", 0)
        congestion_level = cam["current_value"].get("congestion", "여유")
    if led and "current_value" in led:
        led_color = led["current_value"].get("color", "GREEN")

    seat_occupied = False
    if pressure and "current_value" in pressure:
        seat_occupied = pressure["current_value"].get("occupied", False)

    conveyor_running = False
    if conveyor:
        conveyor_running = conveyor.get("current_state") == "on"

    train_data = {
        "current_car": {
            "car_number": 1,
            "title": "1호차 (실시간 AI 모니터링)",
            "person_count": person_count,
            "congestion_level": congestion_level,
            "led_color": led_color,
            "pregnant_seat_occupied": seat_occupied,
            "is_active_monitoring": True,
        },
        "next_car": {
            "car_number": 2,
            "title": "2호차 (인접 객차)",
            "person_count": 2,
            "congestion_level": "여유",
            "led_color": "GREEN",
            "pregnant_seat_occupied": False,
            "is_active_monitoring": False,
        },
        "conveyor": {
            "running": conveyor_running,
            "status_text": "배경 이동 중 (열차 주행 시뮬레이션)" if conveyor_running else "정지 상태",
        },
        "updated_at": datetime.datetime.now().isoformat(),
    }

    return {"data": train_data}
