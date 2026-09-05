"""
Pydantic schemas for IoT devices, sensor readings, and vision events.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class DeviceControlRequest(BaseModel):
    desired_state: str = Field(..., description="목표 상태 (예: 'on', 'off', 'active', 'standby')")
    desired_value: Optional[Union[Dict[str, Any], List[Any], str, int, float]] = Field(
        default=None, description="상세 제어 값 (예: {'color': 'GREEN', 'speed': 50})"
    )
    operator: str = Field(default="user", description="제어 주체 ('user' 또는 'system')")


class DeviceStatusResponse(BaseModel):
    id: str
    name: str
    kind: str
    desired_state: Optional[str] = None
    current_state: Optional[str] = None
    desired_value: Optional[Any] = None
    current_value: Optional[Any] = None
    updated_at: Optional[str] = None
    created_at: Optional[str] = None


class DeviceListResponse(BaseModel):
    devices: List[Dict[str, Any]]


class VisionEventCreate(BaseModel):
    event_type: str = Field(default="person_count", description="이벤트 유형 ('person_count', 'congestion_level')")
    detected: bool = Field(..., description="객체 감지 여부")
    count: int = Field(default=0, ge=0, description="감지된 인원수")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="인식 신뢰도")


class VisionEventResponse(BaseModel):
    id: Optional[int] = None
    event_type: str
    detected: bool
    count: int
    confidence: Optional[float] = None
    congestion_level: str
    led_color: str
    created_at: Optional[str] = None


class PressureSimulateRequest(BaseModel):
    occupied: bool = Field(..., description="임산부석 착석 여부 (True: 착석, False: 비어있음)")
    pressure_val: Optional[float] = Field(default=None, description="시뮬레이션할 압력 수치 (0.0~100.0)")


class TrainCarStatus(BaseModel):
    car_number: int
    person_count: int
    congestion_level: str  # "여유" | "보통" | "혼잡"
    led_color: str         # "GREEN" | "ORANGE" | "RED"
    pregnant_seat_occupied: bool
    conveyor_status: str   # "running" | "stopped"
