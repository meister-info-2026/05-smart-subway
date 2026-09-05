-- ==============================================================================
-- Smart IoT & Vision Control System - Database Initialization Script (MySQL/MariaDB)
-- AI 기반 지하철 객차 혼잡도 실시간 분석 및 임산부석 안내 스마트 시스템
-- ==============================================================================

-- MySQL-only (db-migration 스킬에서 Supabase 전환 시 이 두 줄은 제거한다)
CREATE DATABASE IF NOT EXISTS smart_control
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_control;

-- ------------------------------------------------------------------------------
-- 1. devices: 디바이스 메타데이터 및 실시간 상태 테이블
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS devices (
  id VARCHAR(50) PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  kind VARCHAR(30) NOT NULL,
  desired_state VARCHAR(30) NULL,   -- 대시보드/트리거가 지정한 목표 상태
  current_state VARCHAR(30) NULL,   -- 파이(또는 Mock)가 보고한 실제 상태
  desired_value JSON NULL,          -- on/off로 안 되는 값 (서보 각도, LED 색상/밝기, 모터 속도 등)
  current_value JSON NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------------------------
-- 2. sensor_readings: 센서 측정값 시계열 로그 테이블
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sensor_readings (
  id INT AUTO_INCREMENT PRIMARY KEY, -- MySQL-only
  device_id VARCHAR(50) NOT NULL,
  value FLOAT NULL,
  unit VARCHAR(20) NULL,
  value_json JSON NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------------------------
-- 3. control_log: 디바이스 제어 이력 감사 로그 테이블
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS control_log (
  id INT AUTO_INCREMENT PRIMARY KEY, -- MySQL-only
  device_id VARCHAR(50) NOT NULL,
  action VARCHAR(50) NOT NULL,
  value VARCHAR(100) NULL,
  actor VARCHAR(20) NOT NULL,        -- 'user' 또는 'device'
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------------------------
-- 4. vision_events: 영상인식 모델(YOLO) 감지 이벤트 로그 테이블
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vision_events (
  id INT AUTO_INCREMENT PRIMARY KEY, -- MySQL-only
  event_type VARCHAR(50) NOT NULL,   -- 'person_count', 'congestion_level' 등
  detected BOOLEAN NOT NULL,
  count INT NOT NULL DEFAULT 0,
  confidence FLOAT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------------------------
-- 시드 데이터 (AGENTS.md 팀 정보 기준 디바이스 등록)
-- 재실행해도 중복 에러가 안 나며, 현재 상태(desired_state/current_state)를 덮어쓰지 않도록 구성
-- ------------------------------------------------------------------------------
INSERT INTO devices (id, name, kind) VALUES
  ('led_congestion', '혼잡도 안내 LED', 'led'),
  ('motor_conveyor', '배경 이동 컨베이어', 'motor'),
  ('cam_subway', '객차 Pi Camera 3', 'camera'),
  ('sensor_seat_pressure', '임산부석 압력센서', 'pressure')
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  kind = VALUES(kind);
