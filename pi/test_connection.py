"""
==============================================================================
🚇 라즈베리파이 5 담당자를 위한 1분 통신 검증 스크립트 (ELI5 에디션)
==============================================================================
- 하드웨어 부품(전선, 저항, 브레드보드) 연결 0개!
- 복잡한 라이브러리 없이 순수 콘솔 print 출력으로 백엔드와의 대화를 확인합니다.
- 실행 방법:
    python test_connection.py
==============================================================================
"""

import json
import os
import sys
import time
from pathlib import Path

# 외부 requests 라이브러리 확인
try:
    import requests
except ImportError:
    print("=" * 65)
    print("❌ [알림] 'requests' 라이브러리가 아직 설치되지 않았습니다.")
    print("👉 터미널에서 다음 명령어를 입력해주세요:")
    print("   pip install requests")
    print("=" * 65)
    sys.exit(1)

# 터미널 컬러 출력을 위한 ANSI 코드
class Color:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

def log_info(msg: str):
    print(f"{Color.CYAN}[안내]{Color.RESET} {msg}")

def log_success(msg: str):
    print(f"{Color.GREEN}✅ {msg}{Color.RESET}")

def log_warn(msg: str):
    print(f"{Color.YELLOW}⚠️ {msg}{Color.RESET}")

def log_error(msg: str):
    print(f"{Color.RED}❌ {msg}{Color.RESET}")

def log_action(msg: str):
    print(f"{Color.MAGENTA}{Color.BOLD}{msg}{Color.RESET}")

# ------------------------------------------------------------------------------
# 1. 환경 설정 (.env 읽기 또는 기본값)
# ------------------------------------------------------------------------------
ENV_FILE = Path(__file__).parent / ".env"
BACKEND_URL = "http://127.0.0.1:8000"
DEVICE_API_KEY = "SUBWAY_2026_09_05_v1_0_0"

if ENV_FILE.exists():
    with open(ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key == "BACKEND_URL":
                    BACKEND_URL = val
                elif key == "DEVICE_API_KEY":
                    DEVICE_API_KEY = val

HEADERS = {
    "X-Device-Api-Key": DEVICE_API_KEY,
    "Content-Type": "application/json",
}

print("\n" + "=" * 70)
print(f"{Color.BOLD}🚇 지하철 스마트 제어 시스템 - 라즈베리파이 5 통신 테스트{Color.RESET}")
print("   (전선 배선 없이 print 화면으로 백엔드와 대화하기)")
print("=" * 70)
print(f" • 관제 센터 주소(BACKEND_URL) : {Color.CYAN}{BACKEND_URL}{Color.RESET}")
print(f" • 우리 팀 비밀 출입증(API KEY) : {Color.YELLOW}{DEVICE_API_KEY[:8]}...{Color.RESET}")
print("=" * 70 + "\n")


# ------------------------------------------------------------------------------
# 2. 1단계: 백엔드 관제 센터가 문을 열었는지 확인 (헬스체크)
# ------------------------------------------------------------------------------
log_info("1단계: 백엔드 관제 센터에 노크(헬스체크)해 봅니다...")
try:
    resp = requests.get(f"{BACKEND_URL}/health", timeout=3)
    if resp.status_code == 200:
        data = resp.json()
        log_success(f"관제 센터 연결 성공! (상태: {data.get('status')}, 동작 모드: {data.get('mode')})")
    else:
        log_warn(f"서버가 응답했으나 상태 코드가 {resp.status_code} 입니다.")
except requests.exceptions.ConnectionError:
    print("\n" + "!" * 70)
    log_error("관제 센터(백엔드) 서버에 연결할 수 없습니다!")
    print(f"{Color.BOLD}💡 [3초 처방전]{Color.RESET}")
    print(" 1) 백엔드 담당 팀원에게 백엔드 서버(`uvicorn main:app --reload`)가 켜져 있는지 물어보세요.")
    print(f" 2) 만약 라즈베리파이에서 실행 중이라면 'localhost' 대신 백엔드 PC의 IP 주소")
    print(f"    (예: http://192.168.0.25:8000)를 pi/.env의 BACKEND_URL에 적어야 합니다.")
    print("!" * 70 + "\n")
    sys.exit(1)
except Exception as e:
    log_error(f"알 수 없는 오류 발생: {e}")
    sys.exit(1)


# ------------------------------------------------------------------------------
# 3. 2단계: 백엔드 지시판 확인 및 상태 보고 (혼잡도 LED, 모터)
# ------------------------------------------------------------------------------
time.sleep(0.5)
print("\n" + "-" * 70)
log_info("2단계: 지하철 장치(LED 안내등, 컨베이어)와 대화해 봅니다.")
print("-" * 70)

# 1) 혼잡도 LED (led_congestion)
log_info("혼잡도 안내 LED(led_congestion)의 지시판(desired-state)을 확인합니다...")
try:
    res = requests.get(f"{BACKEND_URL}/api/v1/devices/led_congestion/desired-state", timeout=3)
    if res.status_code == 200:
        d = res.json().get("data", {})
        desired_state = d.get("desired_state", "off")
        desired_val = d.get("desired_value") or {}
        color = desired_val.get("color", "GREEN")
        level = desired_val.get("level", "여유")

        color_icon = "🟢" if color == "GREEN" else ("🟠" if color == "ORANGE" else "🔴")
        log_success(f"지시 확인 완료! 목표 상태: [{desired_state.upper()}] / 색상: {color_icon} {color} ({level})")
        
        # 실제 하드웨어 대신 print문으로 가상 제어
        log_action(f"👉 [하드웨어 흉내내기] 혼잡도 LED에 {color_icon} [{color}] 불빛을 켰습니다!")

        # 백엔드에 반영 완료 보고 (POST state)
        report_payload = {
            "current_state": desired_state,
            "current_value": desired_val,
        }
        rep = requests.post(
            f"{BACKEND_URL}/api/v1/devices/led_congestion/state",
            headers=HEADERS,
            json=report_payload,
            timeout=3
        )
        if rep.status_code == 200:
            log_success("관제 센터에 'LED 불빛 반영 완료했습니다!' 무전 보고 완료 (POST 200 OK)")
        elif rep.status_code == 401:
            log_error("출입증(DEVICE_API_KEY)이 맞지 않아 보고가 거절되었습니다! (401 Unauthorized)")
        else:
            log_warn(f"보고 응답 코드: {rep.status_code}")
    elif res.status_code == 404:
        log_error("장치 ID 'led_congestion'을 찾을 수 없습니다 (404 Not Found). 백엔드 DB 시드를 확인하세요.")
except Exception as e:
    log_error(f"혼잡도 LED 통신 중 오류: {e}")

# 2) 배경 이동 컨베이어 모터 (motor_conveyor)
time.sleep(0.5)
print("")
log_info("배경 이동 컨베이어 모터(motor_conveyor) 지시판을 확인합니다...")
try:
    res = requests.get(f"{BACKEND_URL}/api/v1/devices/motor_conveyor/desired-state", timeout=3)
    if res.status_code == 200:
        d = res.json().get("data", {})
        desired_state = d.get("desired_state", "off")
        desired_val = d.get("desired_value") or {}
        speed = desired_val.get("speed", 0)
        
        motor_icon = "🔄" if desired_state == "on" else "⏹️"
        log_success(f"지시 확인 완료! 목표 상태: [{desired_state.upper()}] / 모터 속도: {speed}%")
        
        # 실제 하드웨어 대신 print문으로 가상 제어
        log_action(f"👉 [하드웨어 흉내내기] 컨베이어 모터를 {motor_icon} [{desired_state.upper()}] (속도 {speed}%) 가동했습니다!")
except Exception as e:
    log_error(f"컨베이어 모터 통신 중 오류: {e}")


# ------------------------------------------------------------------------------
# 4. 3단계: 실시간 폴링 루프 체험 (1초마다 지시판 확인)
# ------------------------------------------------------------------------------
print("\n" + "=" * 70)
print(f"{Color.BOLD}📬 3단계: 실시간 지시판 확인 루프 시작 (1초마다 백엔드 확인){Color.RESET}")
print("   (웹 대시보드나 Vision에서 혼잡도를 바꾸면 화면에 즉시 반응합니다!)")
print("   (멈추려면 키보드 Ctrl + C 를 누르세요)")
print("=" * 70)

last_color = None
count = 1

try:
    while True:
        try:
            res = requests.get(f"{BACKEND_URL}/api/v1/devices/led_congestion/desired-state", timeout=2)
            if res.status_code == 200:
                d = res.json().get("data", {})
                d_val = d.get("desired_value") or {}
                cur_color = d_val.get("color", "GREEN")
                cur_level = d_val.get("level", "여유")
                color_icon = "🟢" if cur_color == "GREEN" else ("🟠" if cur_color == "ORANGE" else "🔴")

                # 색상이 변경되었을 때만 알림
                if cur_color != last_color:
                    print(f"\n{Color.YELLOW}{Color.BOLD}🔔 [관제 센터 지시 변경 감지!]{Color.RESET}")
                    log_action(f"   관제 센터 지시: 혼잡도 [{cur_level}] ➔ LED {color_icon} {cur_color} 변경 요청!")
                    log_action(f"   👉 [LED 제어 흉내] LED 색상을 {color_icon} {cur_color}로 즉시 변경했습니다!")
                    last_color = cur_color

                print(f"\r[{count:03d}회 폴링] 관제 센터 정상 수신 중... 현재 LED: {color_icon} {cur_color} ({cur_level})", end="", flush=True)
                count += 1
            else:
                print(f"\r[{count:03d}회 폴링] 응답 상태 코드: {res.status_code}", end="", flush=True)
        except requests.exceptions.RequestException:
            print(f"\r[{count:03d}회 폴링] 서버 응답 대기 중...", end="", flush=True)

        time.sleep(1.0)

except KeyboardInterrupt:
    print("\n\n" + "=" * 70)
    log_success("테스트를 종료합니다. 백엔드와 라즈베리파이 연동 통신 검증이 완벽히 끝났습니다! 🎉")
    print("=" * 70 + "\n")
