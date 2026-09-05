"""
Mock Device Provider for Windows PC development and simulation.
Implements DeviceProvider interface defined in backend/iot/base.py.
"""

import asyncio
import datetime
import logging
import random
from typing import Any, Dict, List, Optional

from iot.base import DeviceProvider

logger = logging.getLogger("backend.iot.mock_provider")

# DB 모듈 지연/안전 임포트
try:
    from db.database import (
        log_control_action,
        log_sensor_reading,
        update_device_current_state,
        update_device_desired_state,
    )
except ImportError:
    logger.warning("DB module could not be imported. Running in pure in-memory mock mode.")
    log_control_action = None
    log_sensor_reading = None
    update_device_current_state = None
    update_device_desired_state = None


class MockDeviceProvider(DeviceProvider):
    """
    라즈베리파이 5 하드웨어 없이 Windows 환경에서 모든 센서 및 액추에이터 동작을
    100% 시뮬레이션하는 Provider입니다.
    """

    def __init__(self) -> None:
        self._devices: Dict[str, Dict[str, Any]] = {
            "led_congestion": {
                "id": "led_congestion",
                "name": "혼잡도 안내 LED",
                "kind": "led",
                "desired_state": "on",
                "current_state": "on",
                "desired_value": {"color": "GREEN", "level": "여유", "brightness": 100},
                "current_value": {"color": "GREEN", "level": "여유", "brightness": 100},
                "last_actor": "system",
                "updated_at": datetime.datetime.now().isoformat(),
            },
            "motor_conveyor": {
                "id": "motor_conveyor",
                "name": "배경 이동 컨베이어",
                "kind": "motor",
                "desired_state": "off",
                "current_state": "off",
                "desired_value": {"speed": 0, "running": False},
                "current_value": {"speed": 0, "running": False},
                "last_actor": "user",
                "updated_at": datetime.datetime.now().isoformat(),
            },
            "cam_subway": {
                "id": "cam_subway",
                "name": "객차 Pi Camera 3",
                "kind": "camera",
                "desired_state": "active",
                "current_state": "active",
                "desired_value": {"fps": 30},
                "current_value": {"person_count": 0, "congestion": "여유"},
                "last_actor": "system",
                "updated_at": datetime.datetime.now().isoformat(),
            },
            "sensor_seat_pressure": {
                "id": "sensor_seat_pressure",
                "name": "임산부석 압력센서",
                "kind": "pressure",
                "desired_state": None,
                "current_state": "empty",
                "desired_value": None,
                "current_value": {"occupied": False, "pressure_val": 0.0},
                "last_actor": "device",
                "updated_at": datetime.datetime.now().isoformat(),
            },
        }
        logger.info("MockDeviceProvider initialized with subway devices.")

    async def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """특정 디바이스의 최신 상태를 반환합니다."""
        device = self._devices.get(device_id)
        if not device:
            return None
        return dict(device)

    async def set_actuator_state(
        self,
        device_id: str,
        desired_state: str,
        value: Optional[Any] = None,
        operator: str = "user",
    ) -> Dict[str, Any]:
        """
        액추에이터의 목표 상태를 설정하고, Mock 환경에서는 0.1초 후
        실제 상태(current_state)로 자동 반영합니다.
        """
        if device_id not in self._devices:
            raise KeyError(f"Device '{device_id}' not found.")

        dev = self._devices[device_id]
        dev["desired_state"] = desired_state
        if value is not None:
            dev["desired_value"] = value
        dev["last_actor"] = operator
        dev["updated_at"] = datetime.datetime.now().isoformat()

        # DB 목표 상태 갱신 (안전 처리)
        if update_device_desired_state:
            try:
                update_device_desired_state(device_id, desired_state, value)
                log_control_action(device_id, action=f"set_{desired_state}", value=value, actor=operator)
            except Exception as db_exc:
                logger.debug(f"DB update skipped in mock mode: {db_exc}")

        # Mock 시뮬레이션: 즉시 또는 짧은 비동기 딜레이 후 current_state 동기화
        await asyncio.sleep(0.05)
        dev["current_state"] = desired_state
        if value is not None:
            dev["current_value"] = value

        if update_device_current_state:
            try:
                update_device_current_state(device_id, desired_state, value)
            except Exception as db_exc:
                logger.debug(f"DB current state update skipped: {db_exc}")

        return dict(dev)

    async def read_sensor_value(self, device_id: str) -> Dict[str, Any]:
        """
        센서의 최신 측정값을 반환합니다.
        압력센서의 경우 약간의 Random Walk 미세 변동을 주어 생동감을 부여합니다.
        """
        if device_id not in self._devices:
            raise KeyError(f"Device '{device_id}' not found.")

        dev = self._devices[device_id]
        if device_id == "sensor_seat_pressure":
            occupied = dev["current_value"].get("occupied", False)
            if occupied:
                # 착석 중일 때 65.0 ~ 75.0 kg 압력 변동
                val = round(random.uniform(68.0, 72.0), 1)
            else:
                # 빈 좌석일 때 0.0 ~ 0.5 kg 노이즈
                val = round(random.uniform(0.0, 0.4), 1)

            dev["current_value"]["pressure_val"] = val
            dev["current_state"] = "occupied" if occupied else "empty"
            dev["updated_at"] = datetime.datetime.now().isoformat()

            # DB에 센서 수치 기록 (안전 처리)
            if log_sensor_reading:
                try:
                    log_sensor_reading(
                        device_id=device_id,
                        value=val,
                        unit="kg",
                        value_json={"occupied": occupied, "pressure_val": val},
                    )
                except Exception as db_exc:
                    logger.debug(f"DB sensor reading skipped: {db_exc}")

        return dict(dev)

    async def get_all_statuses(self) -> List[Dict[str, Any]]:
        """등록된 모든 디바이스의 최신 상태 목록을 반환합니다."""
        return [dict(dev) for dev in self._devices.values()]

    # --------------------------------------------------------------------------
    # 시뮬레이션 제어 전용 헬퍼 메서드
    # --------------------------------------------------------------------------
    async def simulate_pressure_seat(self, occupied: bool, pressure_val: Optional[float] = None) -> Dict[str, Any]:
        """임산부석 착석/기립 시뮬레이션 상태 변경"""
        dev = self._devices["sensor_seat_pressure"]
        val = pressure_val if pressure_val is not None else (70.0 if occupied else 0.0)
        dev["current_state"] = "occupied" if occupied else "empty"
        dev["current_value"] = {"occupied": occupied, "pressure_val": val}
        dev["updated_at"] = datetime.datetime.now().isoformat()

        if log_sensor_reading:
            try:
                log_sensor_reading(
                    device_id="sensor_seat_pressure",
                    value=val,
                    unit="kg",
                    value_json={"occupied": occupied, "pressure_val": val},
                )
                if update_device_current_state:
                    update_device_current_state("sensor_seat_pressure", dev["current_state"], dev["current_value"])
            except Exception as db_exc:
                logger.debug(f"DB pressure simulation log skipped: {db_exc}")

        return dict(dev)

    async def update_vision_metrics(self, person_count: int, congestion: str, led_color: str) -> None:
        """YOLO 영상인식 결과에 따라 카메라 상태와 혼잡도 LED 상태를 즉시 갱신"""
        cam = self._devices["cam_subway"]
        cam["current_value"] = {"person_count": person_count, "congestion": congestion}
        cam["updated_at"] = datetime.datetime.now().isoformat()

        # LED 혼잡도 안내등 목표/현재 상태 갱신
        led = self._devices["led_congestion"]
        led_val = {"color": led_color, "level": congestion, "brightness": 100}
        led["desired_state"] = "on"
        led["desired_value"] = led_val
        led["current_state"] = "on"
        led["current_value"] = led_val
        led["last_actor"] = "system"
        led["updated_at"] = datetime.datetime.now().isoformat()

        if update_device_current_state:
            try:
                update_device_current_state("cam_subway", "active", cam["current_value"])
                update_device_current_state("led_congestion", "on", led_val)
                if update_device_desired_state:
                    update_device_desired_state("led_congestion", "on", led_val)
            except Exception as db_exc:
                logger.debug(f"DB vision metrics update skipped: {db_exc}")
