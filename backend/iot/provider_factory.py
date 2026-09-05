"""
Provider factory to get the active DeviceProvider instance
based on the DEVICE_MODE environment variable ('mock' or 'hardware').
"""

import os
from typing import Optional
from iot.base import DeviceProvider
from iot.mock_provider import MockDeviceProvider

_provider_instance: Optional[DeviceProvider] = None


def get_device_provider() -> DeviceProvider:
    """
    DEVICE_MODE 환경 변수에 따라 적절한 DeviceProvider 싱글톤 인스턴스를 반환합니다.
    - 'mock': MockDeviceProvider (Windows PC 시뮬레이션 환경)
    - 'hardware': HardwareDeviceProvider (라즈베리파이 5 연동 중계 환경)
    """
    global _provider_instance
    if _provider_instance is None:
        mode = os.getenv("DEVICE_MODE", "mock").lower()
        if mode == "hardware":
            try:
                from iot.hardware_provider import HardwareDeviceProvider
                _provider_instance = HardwareDeviceProvider()
            except ImportError:
                # Hardware provider가 아직 없는 경우 MockProvider로 대체
                _provider_instance = MockDeviceProvider()
        else:
            _provider_instance = MockDeviceProvider()

    return _provider_instance
