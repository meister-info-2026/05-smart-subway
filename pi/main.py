"""
==============================================================================
🚇 AI 스마트 지하철 시스템 - 라즈베리파이 5 하드웨어 데몬 (Daemon)
==============================================================================
- 역할: 백엔드 관제 센터(REST API)와 주기적으로 통신하며 하드웨어를 제어합니다.
- 동작 원리:
    1) 백엔드 목표 상태(desired-state)를 폴링(2초 주기)
    2) 하드웨어 제어 수행 (현재는 실제 핀 제어 대신 시각적 터미널 디버깅 출력)
    3) 실제 반영된 상태(current-state)를 백엔드에 보고(POST state)
    4) 임산부석 압력센서 측정값을 감지하여 백엔드에 실시간 보고
- 하드웨어 확장:
    추후 실제 부품(LED, 모터, 센서) 배선 시 각 Virtual 컨트롤러 클래스 내부의
    주석 처리된 gpiozero 코드를 활성화하면 100% 실기기로 즉시 전환됩니다.
- [필독] 라즈베리파이 5(RP1 칩셋) 주의사항:
    PyPI에서 pip install lgpio 시 C 컴파일 에러가 나므로, 반드시 시스템 APT 패키지
    (sudo apt install -y python3-gpiozero python3-lgpio) 설치 후,
    `python3 -m venv --system-site-packages venv` 가상환경에서 실행하세요.
==============================================================================
"""

import json
import logging
import os
import random
import signal
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# 외부 라이브러리 검사
try:
    import requests
except ImportError:
    print("❌ [오류] 'requests' 라이브러리가 필요합니다. pip install requests 명령어로 설치하세요.")
    sys.exit(1)

# Windows 환경에서 콘솔 UTF-8 인코딩 안전 보장 (이모지 및 한글 깨짐 방지)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    from dotenv import load_dotenv
    # pi/.env 로드
    ENV_PATH = Path(__file__).resolve().parent / ".env"
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH)
except ImportError:
    # python-dotenv 없어도 수동 파싱 지원
    ENV_PATH = Path(__file__).resolve().parent / ".env"
    if ENV_PATH.exists():
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

# 라즈베리파이 5 RP1 칩셋 전용 GPIOZERO Pin Factory 기본값 보장
os.environ.setdefault("GPIOZERO_PIN_FACTORY", "lgpio")


# ==============================================================================
# 1. 터미널 컬러 및 직관적인 디버깅 출력 유틸리티
# ==============================================================================
class TerminalColor:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"


def print_banner(backend_url: str, api_key: str, poll_interval: float):
    masked_key = (api_key[:6] + "..." + api_key[-4:]) if len(api_key) > 10 else "***"
    print("\n" + "=" * 76)
    print(f"{TerminalColor.BOLD}{TerminalColor.CYAN}🚇 AI 스마트 지하철 시스템 — 라즈베리파이 5 통합 제어 데몬{TerminalColor.RESET}")
    print(f"{TerminalColor.DIM}   (하드웨어 가상 디버깅 모드: 물리 핀 제어는 추후 연결 시 전환 가능){TerminalColor.RESET}")
    print("=" * 76)
    print(f" • 관제 센터(백엔드) 주소 : {TerminalColor.BOLD}{backend_url}{TerminalColor.RESET}")
    print(f" • 디바이스 보안 인증 키 : {TerminalColor.YELLOW}{masked_key}{TerminalColor.RESET}")
    print(f" • 상태 동기화 주기(폴링) : {TerminalColor.GREEN}{poll_interval}초{TerminalColor.RESET}")
    print(f" • 관리 대상 디바이스     : led_congestion (혼잡도 안내등)")
    print(f"                           motor_conveyor (배경 이동 컨베이어)")
    print(f"                           sensor_seat_pressure (임산부석 압력센서)")
    print("=" * 76 + "\n")


def log_info(msg: str):
    print(f"{TerminalColor.CYAN}[안내]{TerminalColor.RESET} {msg}")


def log_success(msg: str):
    print(f"{TerminalColor.GREEN}✅ {msg}{TerminalColor.RESET}")


def log_warn(msg: str):
    print(f"{TerminalColor.YELLOW}⚠️  {msg}{TerminalColor.RESET}")


def log_error(msg: str):
    print(f"{TerminalColor.RED}❌ {msg}{TerminalColor.RESET}")


def log_hardware(device_name: str, action: str, details: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n{TerminalColor.MAGENTA}{TerminalColor.BOLD}┌─ 🛠️ [하드웨어 제어] {device_name} ({timestamp}){TerminalColor.RESET}")
    print(f"{TerminalColor.MAGENTA}│  동작: {TerminalColor.BOLD}{action}{TerminalColor.RESET}")
    print(f"{TerminalColor.MAGENTA}└─ 상세: {details}{TerminalColor.RESET}")


# ==============================================================================
# 2. 하드웨어 추상화 계층 (Virtual Hardware Controller)
#    - 현재: 디버깅용 터미널 출력
#    - 추후: gpiozero / lgpio 물리 핀 제어로 교체 가능
# ==============================================================================

class VirtualLedController:
    """
    지하철 객차 혼잡도 안내 LED 컨트롤러 (Virtual Mock)
    - 색상: GREEN (여유), ORANGE (보통), RED (혼잡)
    - 상태: on / off
    """

    def __init__(self, pin_green: int = 17, pin_orange: int = 27, pin_red: int = 22):
        self.pin_green = pin_green
        self.pin_orange = pin_orange
        self.pin_red = pin_red

        self.current_state = "off"
        self.current_color = "GREEN"
        self.current_level = "여유"
        self.brightness = 100

        # 추후 라즈베리파이 5 실기기 연결 시:
        # from gpiozero import LED
        # self.led_g = LED(self.pin_green)
        # self.led_o = LED(self.pin_orange)
        # self.led_r = LED(self.pin_red)

    def apply(self, desired_state: str, desired_value: Optional[Dict[str, Any]]) -> bool:
        """
        목표 상태를 가상 하드웨어에 적용합니다.
        상태나 색상 변경이 발생하면 True를 반환합니다.
        """
        value = desired_value or {}
        color = value.get("color", "GREEN").upper()
        level = value.get("level", "여유")
        brightness = value.get("brightness", 100)

        changed = (
            desired_state != self.current_state
            or color != self.current_color
            or level != self.current_level
        )

        self.current_state = desired_state
        self.current_color = color
        self.current_level = level
        self.brightness = brightness

        if changed:
            icon = "🟢" if color == "GREEN" else ("🟠" if color == "ORANGE" else "🔴")
            if desired_state == "on":
                log_hardware(
                    device_name="혼잡도 안내 LED (led_congestion)",
                    action=f"LED 점등 {icon} [{color}]",
                    details=f"혼잡도 레벨: [{level}] | 밝기: {brightness}% | 핀(가상): G:{self.pin_green}, O:{self.pin_orange}, R:{self.pin_red}",
                )
            else:
                log_hardware(
                    device_name="혼잡도 안내 LED (led_congestion)",
                    action="LED 소등 (OFF)",
                    details="안내등 꺼짐 상태 반영",
                )

        return changed


class VirtualMotorController:
    """
    지하철 주행 시뮬레이션용 배경 이동 컨베이어 모터 컨트롤러 (Virtual Mock)
    - 상태: on / off
    - 속도: 0 ~ 100 (%)
    """

    def __init__(self, pin_forward: int = 23, pin_backward: int = 24, pin_pwm: int = 18):
        self.pin_forward = pin_forward
        self.pin_backward = pin_backward
        self.pin_pwm = pin_pwm

        self.current_state = "off"
        self.speed = 0

        # 추후 실기기 연결 시:
        # from gpiozero import Motor
        # self.motor = Motor(forward=self.pin_forward, backward=self.pin_backward, enable=self.pin_pwm)

    def apply(self, desired_state: str, desired_value: Optional[Dict[str, Any]]) -> bool:
        """
        목표 상태를 가상 모터에 적용합니다.
        변경이 발생하면 True를 반환합니다.
        """
        value = desired_value or {}
        speed = value.get("speed", 50 if desired_state == "on" else 0)

        changed = (desired_state != self.current_state) or (desired_state == "on" and speed != self.speed)

        self.current_state = desired_state
        self.speed = speed

        if changed:
            if desired_state == "on":
                log_hardware(
                    device_name="컨베이어 모터 (motor_conveyor)",
                    action=f"모터 가동 🔄 [ON] (속도 {speed}%)",
                    details=f"배경 이동 시작 (지하철 주행 효과) | PWM 제어핀(가상): GPIO{self.pin_pwm}",
                )
            else:
                log_hardware(
                    device_name="컨베이어 모터 (motor_conveyor)",
                    action="모터 정지 ⏹️ [OFF]",
                    details="배경 이동 중지 (열차 정차 상태)",
                )

        return changed


class VirtualPressureSensor:
    """
    임산부석 착석 감지 압력 센서 (Virtual Mock)
    - 상태: occupied (착석) / empty (비어있음)
    - 압력값: kg 단위
    """

    def __init__(self, pin_adc_ch: int = 0, simulate_random_walk: bool = True):
        self.pin_adc_ch = pin_adc_ch
        self.simulate_random_walk = simulate_random_walk
        self.is_occupied = False
        self.pressure_kg = 0.0
        self._last_toggle_time = time.time()
        self._toggle_interval = 20.0  # 20초마다 시뮬레이션 상태 변경 테스트

        # 추후 MCP3008 ADC 또는 GPIO 실기기 연결 시:
        # from gpiozero import MCP3008
        # self.adc = MCP3008(channel=self.pin_adc_ch)

    def read(self) -> Tuple[str, Dict[str, Any], bool]:
        """
        센서 값을 측정합니다.
        반환값: (state, value_dict, is_changed)
        """
        # 시뮬레이션 모드일 때 일정 주기로 착석/기립 상태 토글
        now = time.time()
        changed = False

        if self.simulate_random_walk:
            if now - self._last_toggle_time > self._toggle_interval:
                self.is_occupied = not self.is_occupied
                self._last_toggle_time = now
                changed = True

            if self.is_occupied:
                self.pressure_kg = round(random.uniform(65.0, 72.0), 1)
            else:
                self.pressure_kg = round(random.uniform(0.0, 0.3), 1)

        state = "occupied" if self.is_occupied else "empty"
        val = {
            "occupied": self.is_occupied,
            "pressure_val": self.pressure_kg,
            "unit": "kg",
        }

        if changed:
            status_text = "🤰 착석 감지됨 (좌석 사용 중)" if self.is_occupied else "💺 기립 감지됨 (좌석 비어있음)"
            log_hardware(
                device_name="임산부석 압력센서 (sensor_seat_pressure)",
                action=f"좌석 상태 변경 ➔ {status_text}",
                details=f"측정 압력: {self.pressure_kg}kg | ADC 채널(가상): CH{self.pin_adc_ch}",
            )

        return state, val, changed


# ==============================================================================
# 3. 백엔드 REST API 통신 클라이언트
# ==============================================================================
class SubwayBackendClient:
    """백엔드와의 REST 통신(GET desired-state, POST state)을 전담하는 클라이언트"""

    def __init__(self, backend_url: str, api_key: str):
        self.base_url = backend_url.rstrip("/")
        self.headers = {
            "X-Device-Api-Key": api_key,
            "Content-Type": "application/json",
        }

    def check_health(self) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """서버 접속 가능 여부 및 동작 모드 확인"""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=3.0)
            if resp.status_code == 200:
                return True, resp.json()
            return False, None
        except Exception:
            return False, None

    def get_desired_state(self, device_id: str) -> Optional[Dict[str, Any]]:
        """특정 액추에이터의 목표 상태 조회 (GET)"""
        url = f"{self.base_url}/api/v1/devices/{device_id}/desired-state"
        try:
            resp = requests.get(url, headers=self.headers, timeout=3.0)
            if resp.status_code == 200:
                return resp.json().get("data", {})
            elif resp.status_code == 404:
                log_warn(f"장치 '{device_id}'를 백엔드 DB에서 찾을 수 없습니다 (404).")
            elif resp.status_code == 401:
                log_error("DEVICE_API_KEY 인증 실패! backend/.env와 pi/.env의 키를 대조하세요.")
            else:
                log_warn(f"[{device_id}] desired-state 조회 응답 코드: {resp.status_code}")
        except requests.exceptions.RequestException as e:
            # 네트워크 순시 오류 시 조용히 넘김 (재시도 루프에서 처리)
            pass
        return None

    def report_device_state(self, device_id: str, state: str, value: Optional[Dict[str, Any]]) -> bool:
        """반영된 상태 또는 센서 측정값 백엔드에 보고 (POST)"""
        url = f"{self.base_url}/api/v1/devices/{device_id}/state"
        payload = {
            "current_state": state,
            "current_value": value,
            "reported_at": datetime.now().isoformat(),
        }
        try:
            resp = requests.post(url, headers=self.headers, json=payload, timeout=3.0)
            if resp.status_code == 200:
                return True
            elif resp.status_code == 401:
                log_error("출입증(DEVICE_API_KEY)이 맞지 않아 상태 보고가 거부되었습니다! (401)")
            else:
                log_warn(f"[{device_id}] 상태 보고 응답 코드: {resp.status_code}")
        except requests.exceptions.RequestException as e:
            log_warn(f"[{device_id}] 상태 보고 전송 실패: {e}")
        return False


# ==============================================================================
# 4. 라즈베리파이 5 메인 데몬 루프 관리자
# ==============================================================================
class SubwayPiDaemon:
    """라즈베리파이 5 백그라운드 데몬"""

    def __init__(self):
        # 환경 변수 로드
        self.backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
        self.api_key = os.getenv("DEVICE_API_KEY", "SUBWAY_2026_09_05_v1_0_0")
        self.poll_interval = float(os.getenv("POLL_INTERVAL_SEC", "2.0"))
        self.simulate_pressure = os.getenv("SIMULATE_PRESSURE_SENSOR", "true").lower() == "true"

        # 통신 클라이언트 및 가상 하드웨어 인스턴스
        self.client = SubwayBackendClient(self.backend_url, self.api_key)
        self.led = VirtualLedController()
        self.motor = VirtualMotorController()
        self.pressure_sensor = VirtualPressureSensor(simulate_random_walk=self.simulate_pressure)

        self._running = True
        self._loop_count = 0

        # 시그널 핸들러 등록 (Ctrl+C 또는 종료 시그널)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        print("\n")
        log_info("종료 신호(SIGINT/SIGTERM)를 수신했습니다. 데몬을 안전하게 종료합니다...")
        self._running = False

    def wait_for_backend_connection(self):
        """백엔드 서버가 연결될 때까지 대기 (로컬 백엔드 자동 감지 폴백 지원)"""
        log_info(f"관제 센터({self.backend_url}) 연결을 확인 중입니다...")
        retry_count = 0
        while self._running:
            ok, data = self.client.check_health()
            if ok:
                mode = data.get("mode", "unknown") if data else "unknown"
                log_success(f"관제 센터 연결 완료! (서버 모드: {mode})")
                return True

            # 만약 원격 IP(예: 192.168.x.x)로 설정되어 접속 실패한 경우, 로컬 127.0.0.1:8000에 백엔드가 떠 있는지 자동 확인
            if "127.0.0.1" not in self.backend_url and "localhost" not in self.backend_url:
                local_client = SubwayBackendClient("http://127.0.0.1:8000", self.api_key)
                local_ok, local_data = local_client.check_health()
                if local_ok:
                    log_warn(f"원격 주소({self.backend_url}) 대신 로컬 PC 관제 센터(http://127.0.0.1:8000)가 감지되었습니다.")
                    log_success("로컬 관제 센터로 자동 연결을 전환합니다. (PC 테스트 모드)")
                    self.backend_url = "http://127.0.0.1:8000"
                    self.client = local_client
                    mode = local_data.get("mode", "unknown") if local_data else "unknown"
                    log_success(f"관제 센터 연결 완료! (서버 모드: {mode})")
                    return True

            retry_count += 1
            if retry_count == 1:
                log_warn(f"관제 센터({self.backend_url})에 연결할 수 없습니다. 3초마다 재시도합니다.")
                print(f"{TerminalColor.DIM}   💡 팁: 백엔드 서버(uvicorn main:app --reload)가 켜져 있는지 확인하세요.{TerminalColor.RESET}")
                print(f"{TerminalColor.DIM}   💡 라즈베리파이에서 실행 중이라면 pi/.env의 BACKEND_URL에 PC IP를 적어주세요.{TerminalColor.RESET}")

            time.sleep(3.0)
        return False

    def run(self):
        """데몬 메인 실행 루프"""
        print_banner(self.backend_url, self.api_key, self.poll_interval)

        if not self.wait_for_backend_connection():
            log_info("데몬이 시작 전에 중단되었습니다.")
            return

        log_success("지하철 하드웨어 모니터링 및 폴링 루프를 시작합니다.")
        print(f"{TerminalColor.DIM}   (종료하려면 언제든지 키보드 Ctrl + C 를 누르세요){TerminalColor.RESET}\n")

        while self._running:
            self._loop_count += 1

            # ------------------------------------------------------------------
            # [1] 혼잡도 안내 LED (led_congestion) 폴링 및 제어
            # ------------------------------------------------------------------
            led_data = self.client.get_desired_state("led_congestion")
            if led_data:
                desired_state = led_data.get("desired_state", "off")
                desired_value = led_data.get("desired_value")
                if self.led.apply(desired_state, desired_value):
                    # 상태 변경 시 백엔드에 즉시 보고
                    self.client.report_device_state(
                        device_id="led_congestion",
                        state=self.led.current_state,
                        value={
                            "color": self.led.current_color,
                            "level": self.led.current_level,
                            "brightness": self.led.brightness,
                        },
                    )

            # ------------------------------------------------------------------
            # [2] 컨베이어 모터 (motor_conveyor) 폴링 및 제어
            # ------------------------------------------------------------------
            motor_data = self.client.get_desired_state("motor_conveyor")
            if motor_data:
                desired_state = motor_data.get("desired_state", "off")
                desired_value = motor_data.get("desired_value")
                if self.motor.apply(desired_state, desired_value):
                    # 상태 변경 시 백엔드에 즉시 보고
                    self.client.report_device_state(
                        device_id="motor_conveyor",
                        state=self.motor.current_state,
                        value={"speed": self.motor.speed, "running": self.motor.current_state == "on"},
                    )

            # ------------------------------------------------------------------
            # [3] 임산부석 압력센서 (sensor_seat_pressure) 상태 측정 및 보고
            # ------------------------------------------------------------------
            seat_state, seat_val, changed = self.pressure_sensor.read()
            # 상태 변경 시 또는 10회 주기마다 1회 동기화 보고
            if changed or (self._loop_count % 10 == 0):
                self.client.report_device_state(
                    device_id="sensor_seat_pressure",
                    state=seat_state,
                    value=seat_val,
                )

            # ------------------------------------------------------------------
            # [4] 터미널 진행 상태 단일 줄 업데이트 (콘솔 깔끔하게 유지)
            # ------------------------------------------------------------------
            led_icon = "🟢" if self.led.current_color == "GREEN" else ("🟠" if self.led.current_color == "ORANGE" else "🔴")
            motor_icon = "🔄 가동" if self.motor.current_state == "on" else "⏹️ 정지"
            seat_icon = "🤰 착석" if self.pressure_sensor.is_occupied else "💺 비어있음"

            status_line = (
                f"\r[{self._loop_count:04d}회 폴링] "
                f"혼잡도 LED: {led_icon} {self.led.current_color}({self.led.current_level}) | "
                f"컨베이어: {motor_icon} | "
                f"임산부석: {seat_icon} ({self.pressure_sensor.pressure_kg}kg)"
            )
            print(status_line, end="", flush=True)

            # 폴링 대기
            time.sleep(self.poll_interval)

        # 안전한 종료 완료 메시지
        print("\n" + "=" * 76)
        log_success("라즈베리파이 5 데몬이 안전하게 종료되었습니다. 수고하셨습니다! 🚇")
        print("=" * 76 + "\n")


# ==============================================================================
# 엔트리포인트
# ==============================================================================
if __name__ == "__main__":
    daemon = SubwayPiDaemon()
    daemon.run()
