import contextlib
import logging
import os
import sys
from typing import Any, Dict, List

# ==============================================================================
# sys.path 자동 경로 주입 (어느 디렉토리에서 실행하든 절대/상대 경로 임포트 오류 방지)
# ==============================================================================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from iot.provider_factory import get_device_provider
from iot.router import router as iot_router
from websocket_manager import ws_manager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("backend.main")

DEFAULT_ALLOWED_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


def get_allowed_origins() -> List[str]:
    """.env의 CORS_ALLOW_ORIGINS를 파싱해 허용 출처 목록을 반환합니다."""
    raw = os.getenv("CORS_ALLOW_ORIGINS", DEFAULT_ALLOWED_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작 및 종료 라이프사이클 관리: DB 초기화 및 프로바이더 준비"""
    logger.info("Initializing Subway Smart Control Backend...")
    # 1. DB 초기화 시도
    try:
        from db.database import init_db
        init_db()
        logger.info("MySQL database initialized successfully.")
    except Exception as exc:
        logger.warning(
            f"Database initialization failed ({exc}). "
            "Running in standalone Mock mode. Data will be kept in memory."
        )

    # 2. 디바이스 프로바이더 인스턴스 초기화
    provider = get_device_provider()
    logger.info(f"Device provider ready: {provider.__class__.__name__}")

    yield

    logger.info("Shutting down Subway Smart Control Backend...")


app = FastAPI(
    title="AI Smart Subway Control System API",
    version="1.0.0",
    description="지하철 객차 혼잡도 분석 및 임산부석 안내 스마트 제어 시스템 백엔드 API",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(iot_router)


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """백엔드 서버 헬스체크 엔드포인트"""
    return {
        "status": "ok",
        "message": "Subway Smart Control backend is healthy.",
        "mode": os.getenv("DEVICE_MODE", "mock"),
    }


@app.get("/")
async def root() -> Dict[str, Any]:
    """루트 안내 엔드포인트"""
    return {
        "system": "지하철 객차 혼잡도 및 임산부석 안내 스마트 시스템",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_url": "/health",
        "api_v1": "/api/v1/devices",
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    실시간 디바이스 상태 및 비전 이벤트 스트리밍용 WebSocket 엔드포인트
    클라이언트 연결 시 현재 디바이스들의 초기 상태를 즉시 전송합니다.
    """
    await ws_manager.connect(websocket)
    provider = get_device_provider()
    try:
        # 1. 연결 직후 전체 디바이스 최신 상태 1회 전송
        initial_devices = await provider.get_all_statuses()
        await websocket.send_json({
            "type": "initial_state",
            "devices": initial_devices,
        })

        # 2. 클라이언트 연결 유지 및 수신 대기
        while True:
            # 클라이언트로부터 핑 또는 메시지 수신 대기
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning(f"WebSocket closed with exception: {exc}")
        ws_manager.disconnect(websocket)
