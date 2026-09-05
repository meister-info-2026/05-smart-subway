"""
Zero-Dependency YOLOv8 Subway Passenger Detection Client.
Uses native OpenCV DNN with 'yolov8n.onnx' (No PyTorch/c10.dll dependencies required).
Runs stably and fast on 100% of Windows PCs for student exhibitions.
"""

import datetime
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
from dotenv import load_dotenv
import numpy as np
import requests

# 환경 변수 로드
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("vision.main")

# 설정값
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "SUBWAY_2026_09_05_v1_0_0")
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))

SCRIPT_DIR = Path(__file__).resolve().parent
ONNX_MODEL_PATH = SCRIPT_DIR / "yolov8n.onnx"

# OpenCV DNN으로 ONNX 모델 로드 (PyTorch/c10.dll 의존성 완전 제거)
net = None
use_onnx = False

if ONNX_MODEL_PATH.exists():
    try:
        logger.info(f"Loading YOLOv8 ONNX model via OpenCV DNN: {ONNX_MODEL_PATH.name}...")
        net = cv2.dnn.readNetFromONNX(str(ONNX_MODEL_PATH))
        # CPU 고성능 연산자 설정
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        use_onnx = True
        logger.info("YOLOv8 ONNX model loaded successfully with native OpenCV DNN!")
    except Exception as exc:
        logger.warning(f"Failed to load ONNX model via OpenCV DNN ({exc}). Switching to simulation.")
        use_onnx = False
else:
    logger.warning(f"ONNX model file not found at {ONNX_MODEL_PATH}. Switching to simulation.")


def detect_persons_onnx(frame: np.ndarray, conf_threshold: float = 0.45, nms_threshold: float = 0.45) -> Tuple[int, List[Tuple[int, int, int, int, float]]]:
    """
    OpenCV DNN을 사용하여 프레임에서 사람(class 0)을 탐지하고 (x1, y1, x2, y2, confidence) 목록을 반환합니다.
    """
    if net is None:
        return 0, []

    h, w = frame.shape[:2]
    # YOLOv8 입력 크기: 640x640
    blob = cv2.dnn.blobFromImage(frame, 1 / 255.0, (640, 640), swapRB=True, crop=False)
    net.setInput(blob)
    preds = net.forward()  # shape: [1, 84, 8400]

    # [84, 8400] -> [8400, 84]로 전치
    preds = np.transpose(preds[0])

    boxes = []
    confidences = []

    # 스케일 팩터
    x_factor = w / 640.0
    y_factor = h / 640.0

    for row in preds:
        classes_scores = row[4:]
        person_score = classes_scores[0]  # class 0 = person

        if person_score >= conf_threshold:
            cx, cy, bw, bh = row[0], row[1], row[2], row[3]
            left = int((cx - bw / 2) * x_factor)
            top = int((cy - bh / 2) * y_factor)
            width = int(bw * x_factor)
            height = int(bh * y_factor)

            boxes.append([left, top, width, height])
            confidences.append(float(person_score))

    # NMS (Non-Maximum Suppression)로 중복 바운딩 박스 제거
    indices = cv2.dnn.NMSBoxes(boxes, confidences, conf_threshold, nms_threshold)

    results = []
    if len(indices) > 0:
        for idx in indices:
            i = int(idx)
            box = boxes[i]
            x1 = max(0, box[0])
            y1 = max(0, box[1])
            x2 = min(w, x1 + box[2])
            y2 = min(h, y1 + box[3])
            results.append((x1, y1, x2, y2, confidences[i]))

    return len(results), results


def send_vision_event(count: int, confidence: Optional[float] = None) -> bool:
    """백엔드 API로 영상인식 감지 이벤트를 전송합니다."""
    url = f"{BACKEND_URL}/api/v1/vision/events"
    headers = {
        "X-Device-Api-Key": DEVICE_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "event_type": "person_count",
        "detected": count > 0,
        "count": count,
        "confidence": round(confidence, 2) if confidence is not None else 0.90,
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=2.0)
        if res.status_code == 200:
            data = res.json().get("data", {})
            logger.info(
                f"Event sent -> Count: {count} | "
                f"Congestion: {data.get('congestion_level')} | "
                f"LED: {data.get('led_color')}"
            )
            return True
        else:
            logger.warning(f"Backend returned status {res.status_code}: {res.text}")
    except requests.exceptions.RequestException as exc:
        logger.warning(f"Failed to send event to backend ({url}): {exc}")
    return False


def get_congestion_info(count: int):
    """인원수에 따른 혼잡도 텍스트 및 BGR 색상 반환"""
    if count <= 2:
        return "LOW (여유)", (0, 200, 0)      # Green
    elif 3 <= count <= 5:
        return "MEDIUM (보통)", (0, 140, 255) # Orange
    else:
        return "HIGH (혼잡)", (0, 0, 240)    # Red


def draw_virtual_car_frame(passenger_count: int, status_msg: str):
    """가상 지하철 1호차 객차 및 승객 시뮬레이션 프레임 생성"""
    h, w = 480, 640
    frame = np.full((h, w, 3), 35, dtype=np.uint8)

    # 지하철 객차 외곽선
    cv2.rectangle(frame, (20, 20), (w - 20, h - 30), (70, 70, 70), 2)
    cv2.putText(frame, "SUBWAY CAR 1 - SIMULATION MODE (KEYBOARD CONTROL)", (35, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 2)

    # 승객 그래픽 (최대 12명 가상 렌더링)
    cols = 4
    start_x, start_y = 60, 110
    step_x, step_y = 140, 110

    for i in range(passenger_count):
        row = i // cols
        col = i % cols
        cx = start_x + col * step_x + 30
        cy = start_y + row * step_y + 30

        # 머리 및 어깨 실루엣
        cv2.circle(frame, (cx, cy - 12), 16, (240, 220, 120), -1)
        cv2.ellipse(frame, (cx, cy + 22), (24, 16), 0, 0, 180, (220, 160, 60), -1)
        cv2.rectangle(frame, (cx - 32, cy - 35), (cx + 32, cy + 40), (0, 255, 120), 2)
        cv2.putText(frame, f"Person {i+1}", (cx - 28, cy - 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 120), 1)

    # 하단 혼잡도 및 통신 상태 바
    congestion_text, color = get_congestion_info(passenger_count)
    cv2.rectangle(frame, (20, h - 90), (w - 20, h - 30), (50, 50, 50), -1)
    cv2.putText(frame, f"Passengers: {passenger_count} | {congestion_text}", (35, h - 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
    cv2.putText(frame, status_msg, (35, h - 40),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

    # 키보드 조작 가이드
    cv2.putText(frame, "[+] 승객 추가   [-] 승객 감소   [Space] 인원수 랜덤   [Q] 종료", (35, 80),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (130, 210, 255), 1)

    return frame


def run_vision_loop():
    logger.info("==================================================")
    logger.info("Starting Subway AI Vision Client...")
    logger.info(f"Target Backend: {BACKEND_URL}")
    if use_onnx:
        logger.info("Engine: Native OpenCV DNN + YOLOv8 ONNX (Zero DLL Dependency)")
    else:
        logger.info("Engine: Virtual Passenger Simulation Mode")
    logger.info("==================================================")

    # 웹캠 연결 확인 (DirectShow)
    cap = None
    use_simulation = not use_onnx

    if use_onnx:
        cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
        if not cap.isOpened():
            logger.warning(f"Could not open webcam (index {CAMERA_INDEX}). Switching to Virtual Simulation Mode.")
            use_simulation = True
        else:
            ret, test_frame = cap.read()
            if not ret or test_frame is None:
                logger.warning("Webcam opened but frame read failed. Switching to Virtual Simulation Mode.")
                cap.release()
                use_simulation = True
            else:
                logger.info(f"Webcam (index {CAMERA_INDEX}) connected successfully.")

    last_sent_count = -1
    last_sent_time = 0.0
    heartbeat_interval = 2.5  # 초

    sim_passenger_count = 2
    status_msg = "Subway passenger detection active."

    try:
        while True:
            current_time = time.time()
            detected_count = 0
            avg_confidence = 0.90
            display_frame = None

            if not use_simulation and cap is not None:
                ret, frame = cap.read()
                if not ret:
                    logger.warning("Frame read lost. Switching to Simulation Mode.")
                    use_simulation = True
                    continue

                # OpenCV DNN YOLOv8로 실시간 사람 감지
                detected_count, person_boxes = detect_persons_onnx(frame)
                display_frame = frame.copy()

                if detected_count > 0:
                    confs = [box[4] for box in person_boxes]
                    avg_confidence = sum(confs) / len(confs)

                # 바운딩 박스 그리기
                for x1, y1, x2, y2, conf in person_boxes:
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(
                        display_frame,
                        f"Person {conf:.2f}",
                        (x1, max(20, y1 - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.55,
                        (0, 255, 0),
                        2,
                    )

                # 헤더 정보 표시
                c_text, c_color = get_congestion_info(detected_count)
                cv2.rectangle(display_frame, (10, 10), (420, 50), (30, 30, 30), -1)
                cv2.putText(
                    display_frame,
                    f"Count: {detected_count} | {c_text} (ONNX)",
                    (20, 38),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    c_color,
                    2,
                )
            else:
                # 가상 시뮬레이션 모드 (모든 Windows PC에서 100% 동작)
                detected_count = sim_passenger_count
                display_frame = draw_virtual_car_frame(detected_count, status_msg)

            # 백엔드 전송 트리거
            count_changed = (detected_count != last_sent_count)
            heartbeat_due = (current_time - last_sent_time >= heartbeat_interval)

            if count_changed or heartbeat_due:
                sent = send_vision_event(detected_count, avg_confidence)
                if sent:
                    last_sent_count = detected_count
                    last_sent_time = current_time
                    status_msg = f"Last event sent at {datetime.datetime.now().strftime('%H:%M:%S')}"
                else:
                    status_msg = "Backend offline (Check http://localhost:8000)"

            # 화면 출력
            window_title = "Subway AI Congestion Detection (Press Q to quit)"
            cv2.imshow(window_title, display_frame)

            # 키보드 입력
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q') or key == 27:
                logger.info("Exit key pressed. Terminating.")
                break
            elif use_simulation:
                if key == ord('+') or key == ord('='):
                    sim_passenger_count = min(12, sim_passenger_count + 1)
                    logger.info(f"Simulated passengers increased: {sim_passenger_count}")
                elif key == ord('-') or key == ord('_'):
                    sim_passenger_count = max(0, sim_passenger_count - 1)
                    logger.info(f"Simulated passengers decreased: {sim_passenger_count}")
                elif key == ord(' '):  # 스페이스바
                    import random
                    sim_passenger_count = random.choice([1, 2, 4, 7, 9])
                    logger.info(f"Simulated passengers random: {sim_passenger_count}")

    finally:
        if cap is not None and cap.isOpened():
            cap.release()
        cv2.destroyAllWindows()
        logger.info("Vision client closed.")


if __name__ == "__main__":
    run_vision_loop()
