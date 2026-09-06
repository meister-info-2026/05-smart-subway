"""
test_hardware_gpio.py
--------------------------------------------------------------------------------
[라즈베리파이 5 담당자를 위한 하드웨어 배선 및 GPIO 1분 자가진단 도구]

* 목적:
  - 백엔드 연결 전, 라즈베리파이 5의 물리 부품(혼잡도 3색 LED, 컨베이어 모터, 임산부석 압력센서)이
    정상 작동하는지 자가진단합니다.
  - RP1 칩셋 환경에서 lgpio 및 gpiozero 핀 팩토리가 정상 로드되는지 검증합니다.

* 실행 방법 (라즈베리파이 터미널):
  python test_hardware_gpio.py
--------------------------------------------------------------------------------
"""

import os
import sys
import time
from dotenv import load_dotenv

# Windows 환경 콘솔 UTF-8 인코딩 안전 보장 (이모지 및 한글 깨짐 방지)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

load_dotenv()

# GPIOZERO Pin Factory 기본값 설정 (라즈베리파이 5 RP1 칩셋 전용)
os.environ.setdefault("GPIOZERO_PIN_FACTORY", "lgpio")

print("=" * 65)
print("🍓 [라즈베리파이 5] 지하철 스마트 제어 시스템 - GPIO 배선 자가진단")
print("=" * 65)

# 1. gpiozero 및 lgpio 라이브러리 로드 검사
try:
    from gpiozero import LED, OutputDevice, DigitalInputDevice, Button
    from gpiozero.pins.lgpio import LGPIOFactory
    print("✅ [패키지 확인] gpiozero 및 lgpio 모듈이 정상적으로 로드되었습니다.")
except ImportError as e:
    print("\n⚠️ [패키지 오류] gpiozero 또는 lgpio 라이브러리를 찾을 수 없습니다.")
    print("라즈베리파이 5(RP1 칩셋)에서는 PyPI pip 빌드 오류(C 컴파일 에러)를 방지하기 위해")
    print("OS 기본 APT 패키지와 --system-site-packages 가상환경을 사용해야 합니다.\n")
    print("  1) 시스템 APT 패키지 설치:")
    print("     sudo apt update && sudo apt install -y python3-gpiozero python3-lgpio\n")
    print("  2) 가상환경 생성 (시스템 패키지 상속):")
    print("     cd pi")
    print("     python3 -m venv --system-site-packages venv")
    print("     source venv/bin/activate\n")
    print("  3) 필수 Python 의존성 설치:")
    print("     pip install -r requirements.txt\n")
    if sys.platform == "win32":
        print("💡 (안내: 현재 Windows PC 환경입니다. 실기기 GPIO 배선 테스트는 실제 라즈베리파이 5에서 실행하세요.)")
    sys.exit(0 if sys.platform == "win32" else 1)

# 2. 핀 번호 정의 (docs/01 매뉴얼 및 pi/main.py 기준)
PIN_LED_GREEN = int(os.getenv("PIN_LED_GREEN", "17"))
PIN_LED_ORANGE = int(os.getenv("PIN_LED_ORANGE", "27"))
PIN_LED_RED = int(os.getenv("PIN_LED_RED", "22"))
PIN_MOTOR_CONVEYOR = int(os.getenv("PIN_MOTOR_CONVEYOR", "23"))
PIN_SENSOR_PRESSURE = int(os.getenv("PIN_SENSOR_PRESSURE", "24"))

print(f"\n[할당된 GPIO 핀 목록 (BCM 번호)]")
print(f"  - 혼잡도 초록 LED (여유) : GPIO {PIN_LED_GREEN}")
print(f"  - 혼잡도 주황 LED (보통) : GPIO {PIN_LED_ORANGE}")
print(f"  - 혼잡도 빨강 LED (혼잡) : GPIO {PIN_LED_RED}")
print(f"  - 배경 컨베이어 모터    : GPIO {PIN_MOTOR_CONVEYOR}")
print(f"  - 임산부석 압력센서      : GPIO {PIN_SENSOR_PRESSURE}")
print("-" * 65)


def test_hardware():
    try:
        # 3. 혼잡도 안내 3색 LED 테스트
        print("\n🟢 [1/3] 혼잡도 삼색등 LED 순차 점등 테스트를 시작합니다...")
        led_g = LED(PIN_LED_GREEN)
        led_o = LED(PIN_LED_ORANGE)
        led_r = LED(PIN_LED_RED)

        print("  - 🟢 초록 LED ON (여유 레벨)")
        led_g.on()
        time.sleep(1)
        led_g.off()

        print("  - 🟠 주황 LED ON (보통 레벨)")
        led_o.on()
        time.sleep(1)
        led_o.off()

        print("  - 🔴 빨강 LED ON (혼잡 레벨)")
        led_r.on()
        time.sleep(1)
        led_r.off()

        print("  - 🚦 전체 LED 동시 점등 (1초)")
        led_g.on()
        led_o.on()
        led_r.on()
        time.sleep(1)
        led_g.off()
        led_o.off()
        led_r.off()
        print("  ✅ 혼잡도 LED 테스트 완료!")

        # 4. 배경 컨베이어 모터 테스트
        print("\n🔄 [2/3] 배경 컨베이어 모터(릴레이) 가동 테스트를 시작합니다...")
        motor = OutputDevice(PIN_MOTOR_CONVEYOR, active_high=True, initial_value=False)
        print("  - 모터 가동 ON (1.5초)")
        motor.on()
        time.sleep(1.5)
        print("  - 모터 정지 OFF")
        motor.off()
        print("  ✅ 컨베이어 모터 제어 테스트 완료!")

        # 5. 임산부석 압력 센서 테스트
        print(f"\n🪑 [3/3] 임산부석 압력센서(GPIO {PIN_SENSOR_PRESSURE}) 입력 감지 테스트 (5초간 대기)...")
        print("  👉 센서나 버튼을 눌러보세요 (누르면 화면에 실시간 표시됩니다)")
        
        sensor = Button(PIN_SENSOR_PRESSURE, pull_up=True)
        start_time = time.time()
        pressed = False

        while time.time() - start_time < 5.0:
            remaining = int(5.0 - (time.time() - start_time))
            if sensor.is_pressed:
                print(f"\r  💥 [감지됨!] 임산부석 압력센서 접촉 감지! (센서 ON)        ", flush=True)
                pressed = True
            else:
                state_str = "착석 감지됨" if pressed else "비어 있음"
                print(f"\r  ⏳ 감지 대기 중... ({remaining}초 남음) | 현재 상태: {state_str}   ", end="", flush=True)
            time.sleep(0.2)
        
        print("\n  ✅ 압력센서 입력 테스트 완료!")

        # 자원 정리
        led_g.close()
        led_o.close()
        led_r.close()
        motor.close()
        sensor.close()

        print("\n" + "=" * 65)
        print("🎉 [축하합니다] 라즈베리파이 5 모든 하드웨어 부품 자가진단에 통과했습니다!")
        print("👉 이제 'python main.py'를 실행하여 백엔드 실시간 연동 데몬을 구동하세요.")
        print("=" * 65 + "\n")

    except Exception as exc:
        print(f"\n❌ [테스트 실패] 하드웨어 제어 중 에러가 발생했습니다: {exc}")
        print("💡 점검 체크리스트:")
        print("  1. 배선 핀 번호(BCM 기준)가 올바른지 확인하세요.")
        print("  2. GND 선이 브레드보드 및 부품과 공통으로 잘 연결되었는지 확인하세요.")
        print("  3. pi/.env 파일의 GPIOZERO_PIN_FACTORY=lgpio 설정이 되어 있는지 확인하세요.\n")


if __name__ == "__main__":
    test_hardware()
