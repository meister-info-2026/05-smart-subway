import json
import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional, Union

from dotenv import load_dotenv
import pymysql
import pymysql.cursors

# .env 로드 (backend/.env 우선 로드)
load_dotenv()

logger = logging.getLogger("backend.db")

# 데이터베이스 연결 설정
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "smart_control")


def get_db_connection(database: Optional[str] = DB_NAME) -> pymysql.Connection:
    """
    MySQL/MariaDB 데이터베이스 연결 객체를 생성하여 반환합니다.
    """
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


@contextmanager
def get_db_cursor(
    commit: bool = False, database: Optional[str] = DB_NAME
) -> Generator[pymysql.cursors.DictCursor, None, None]:
    """
    안전한 트랜잭션 및 커서 관리를 위한 contextmanager입니다.
    """
    conn = get_db_connection(database=database)
    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error(f"Database error during transaction: {exc}")
        raise
    finally:
        cursor.close()
        conn.close()


def init_db() -> None:
    """
    서버 시작 시 데이터베이스 및 필요한 테이블이 존재하는지 확인하고,
    미존재 시 초기 스키마를 생성합니다.
    """
    try:
        # 1. 데이터베이스 존재 여부 확인 및 생성
        server_conn = get_db_connection(database=None)
        with server_conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
        server_conn.commit()
        server_conn.close()

        # 2. 필수 테이블 스키마 DDL 생성
        with get_db_cursor(commit=True) as cur:
            # devices 테이블
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    kind VARCHAR(30) NOT NULL,
                    desired_state VARCHAR(30) NULL,
                    current_state VARCHAR(30) NULL,
                    desired_value JSON NULL,
                    current_value JSON NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # sensor_readings 테이블
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id INT AUTO_INCREMENT PRIMARY KEY, -- MySQL-only
                    device_id VARCHAR(50) NOT NULL,
                    value FLOAT NULL,
                    unit VARCHAR(20) NULL,
                    value_json JSON NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
                );
                """
            )

            # control_log 테이블
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS control_log (
                    id INT AUTO_INCREMENT PRIMARY KEY, -- MySQL-only
                    device_id VARCHAR(50) NOT NULL,
                    action VARCHAR(50) NOT NULL,
                    value VARCHAR(100) NULL,
                    actor VARCHAR(20) NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
                );
                """
            )

            # vision_events 테이블
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS vision_events (
                    id INT AUTO_INCREMENT PRIMARY KEY, -- MySQL-only
                    event_type VARCHAR(50) NOT NULL,
                    detected BOOLEAN NOT NULL,
                    count INT NOT NULL DEFAULT 0,
                    confidence FLOAT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

            # AGENTS.md 팀 정보 기본 시드 디바이스 삽입
            seed_devices = [
                ("led_congestion", "혼잡도 안내 LED", "led"),
                ("motor_conveyor", "배경 이동 컨베이어", "motor"),
                ("cam_subway", "객차 Pi Camera 3", "camera"),
                ("sensor_seat_pressure", "임산부석 압력센서", "pressure"),
            ]
            cur.executemany(
                """
                INSERT INTO devices (id, name, kind)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    kind = VALUES(kind);
                """,
                seed_devices,
            )

        logger.info("Database schema and seed devices initialized successfully.")
    except Exception as exc:
        logger.error(f"Failed to initialize database: {exc}")
        raise


def _parse_json_fields(device: Dict[str, Any]) -> Dict[str, Any]:
    """JSON 문자열로 반환될 수 있는 필드를 딕셔너리나 리스트 객체로 역직렬화합니다."""
    for field in ("desired_value", "current_value", "value_json"):
        if field in device and isinstance(device[field], str):
            try:
                device[field] = json.loads(device[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return device


def log_sensor_reading(
    device_id: str,
    value: Optional[float] = None,
    unit: Optional[str] = None,
    value_json: Optional[Union[Dict[str, Any], List[Any], str]] = None,
) -> None:
    """
    센서 측정값을 sensor_readings 테이블에 기록합니다.
    단일 수치는 value+unit을, 다중 측정값은 value_json을 사용합니다.
    """
    json_str = None
    if value_json is not None:
        json_str = value_json if isinstance(value_json, str) else json.dumps(value_json, ensure_ascii=False)

    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO sensor_readings (device_id, value, unit, value_json)
            VALUES (%s, %s, %s, %s);
            """,
            (device_id, value, unit, json_str),
        )


def log_control_action(
    device_id: str,
    action: str,
    value: Any = None,
    actor: str = "user",
) -> None:
    """
    디바이스 제어 이력을 control_log 테이블에 기록합니다.
    actor는 'user' 또는 'device'입니다.
    """
    str_value = str(value) if value is not None else None
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO control_log (device_id, action, value, actor)
            VALUES (%s, %s, %s, %s);
            """,
            (device_id, action, str_value, actor),
        )


def get_sensor_history(device_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    특정 센서의 최근 측정값 기록을 조회합니다.
    """
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            """
            SELECT id, device_id, value, unit, value_json, created_at
            FROM sensor_readings
            WHERE device_id = %s
            ORDER BY created_at DESC
            LIMIT %s;
            """,
            (device_id, limit),
        )
        rows = cur.fetchall()
        return [_parse_json_fields(row) for row in rows]


def log_vision_event(
    event_type: str,
    detected: bool,
    count: int = 0,
    confidence: Optional[float] = None,
) -> None:
    """
    영상인식 감지 이벤트를 vision_events 테이블에 기록합니다.
    """
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO vision_events (event_type, detected, count, confidence)
            VALUES (%s, %s, %s, %s);
            """,
            (event_type, detected, count, confidence),
        )


def get_device(device_id: str) -> Optional[Dict[str, Any]]:
    """
    특정 디바이스의 최신 상태 정보를 조회합니다.
    """
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            """
            SELECT id, name, kind, desired_state, current_state,
                   desired_value, current_value, updated_at, created_at
            FROM devices
            WHERE id = %s;
            """,
            (device_id,),
        )
        row = cur.fetchone()
        return _parse_json_fields(row) if row else None


def get_all_devices() -> List[Dict[str, Any]]:
    """
    등록된 모든 디바이스 목록 및 상태를 조회합니다.
    """
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            """
            SELECT id, name, kind, desired_state, current_state,
                   desired_value, current_value, updated_at, created_at
            FROM devices
            ORDER BY created_at ASC;
            """
        )
        rows = cur.fetchall()
        return [_parse_json_fields(row) for row in rows]


def update_device_desired_state(
    device_id: str,
    desired_state: Optional[str],
    desired_value: Optional[Any] = None,
) -> bool:
    """
    대시보드 또는 트리거 로직에서 지정한 액추에이터의 목표 상태(desired_state / desired_value)를 갱신합니다.
    """
    json_str = None
    if desired_value is not None:
        json_str = (
            desired_value
            if isinstance(desired_value, str)
            else json.dumps(desired_value, ensure_ascii=False)
        )

    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE devices
            SET desired_state = %s,
                desired_value = %s
            WHERE id = %s;
            """,
            (desired_state, json_str, device_id),
        )
        return cur.rowcount > 0


def update_device_current_state(
    device_id: str,
    current_state: Optional[str],
    current_value: Optional[Any] = None,
) -> bool:
    """
    라즈베리파이(또는 Mock)가 보고한 실제 상태(current_state / current_value)를 갱신합니다.
    """
    json_str = None
    if current_value is not None:
        json_str = (
            current_value
            if isinstance(current_value, str)
            else json.dumps(current_value, ensure_ascii=False)
        )

    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE devices
            SET current_state = %s,
                current_value = %s
            WHERE id = %s;
            """,
            (current_state, json_str, device_id),
        )
        return cur.rowcount > 0
