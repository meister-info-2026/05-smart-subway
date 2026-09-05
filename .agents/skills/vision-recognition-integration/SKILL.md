---
name: vision-recognition-integration
description: >-
  웹캠 기반 YOLOv8/mediapipe 영상인식 파이프라인 구성, Windows 패키지 의존성 설정 및 감지 이벤트 백엔드 전송을 구현할 때 사용하는 스킬.
---

# vision-recognition-integration

> 웹캠 영상인식(YOLO/mediapipe) 연동 작업 시 이 스킬을 참고한다.

## 패키지 설치 (Windows 안정화 표준)
Windows 환경에서 Python 3.14/3.13 설치 시 발생하는 C-확장 모듈 DLL 로드 에러(`[WinError 1114]`)를 방지하고, 
2GB 상당의 무거운 PyTorch와 Windows 긴 경로 에러(`[WinError 206]`)를 원천 차단하기 위해 
**`py -3.12` 가상환경** 및 **Native OpenCV DNN (`yolov8n.onnx`)** 방식을 사용한다.
`.gitignore` 호환을 위해 가상환경 폴더명은 반드시 `venv`로 통일한다.

```powershell
cd vision
# Python 3.12 가상환경 생성 (3.12 미설치 시 python -m venv venv)
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1

# 경량 패키지 설치 (OpenCV, NumPy, Pillow, Requests - 약 50MB, 10초 내 완료)
pip install -r requirements.txt
```

## 최소 파이프라인 (Native OpenCV DNN + YOLOv8 ONNX 조합)
PyTorch 의존성 없이 순수 OpenCV DNN으로 `yolov8n.onnx`를 로드하여 객차 내 사람(class 0)을 탐지한다.
웹캠 한글 깨짐 방지 및 라벨링을 위해 `PIL(Pillow)`을 활용할 수 있다.

```python
import cv2
import numpy as np

# OpenCV DNN으로 ONNX 모델 로드 (PyTorch/c10.dll 불필요)
net = cv2.dnn.readNetFromONNX("yolov8n.onnx")
net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Windows에서는 CAP_DSHOW로 열어야 웹캠 인식이 안정적

while True:
    ok, frame = cap.read()
    if not ok:
        continue
    # 640x640 blob 변환 후 추론
    blob = cv2.dnn.blobFromImage(frame, 1/255.0, (640, 640), swapRB=True, crop=False)
    net.setInput(blob)
    preds = net.forward()
    # 인원수 판별 후 백엔드 전송 (vision/main.py 참고)
```

<details>
<summary>mediapipe로도 가능 (얼굴 감지 등 다른 용도일 때)</summary>

```python
import cv2
import mediapipe as mp

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
detector = mp.solutions.face_detection.FaceDetection()

while True:
    ok, frame = cap.read()
    if not ok:
        continue
    result = detector.process(frame)
    detected = bool(result.detections)
```
</details>

## 이벤트 전송
```python
import requests
requests.post(
    f"{BACKEND_URL}/api/v1/vision/events",
    json={"event_type": "person_detected", "detected": True, "count": 1, "confidence": 0.9},
    headers={"X-Device-Api-Key": DEVICE_API_KEY},
)
```

## 트리거 연결
백엔드(backend-agent)가 `vision_events`를 받아 팀이 정한 트리거 규칙(AGENTS.md의
"팀 정보" 표 참고)에 따라 desired-state를 갱신한다. vision 클라이언트는 감지 사실만
보고할 뿐, 제어를 직접 판단하지 않는다.
