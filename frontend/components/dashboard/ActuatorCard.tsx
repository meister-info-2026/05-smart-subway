"use client";

import React, { useState } from "react";
import { DeviceInfo } from "@/hooks/useSubwaySocket";
import { getStatusBadgeClass } from "@/components/dashboard/statusColor";

interface ActuatorCardProps {
  device: DeviceInfo;
  onControl: (deviceId: string, desiredState: string, desiredValue?: unknown) => Promise<boolean>;
}

export const ActuatorCard: React.FC<ActuatorCardProps> = ({ device, onControl }) => {
  const [loading, setLoading] = useState(false);

  const isLed = device.id === "led_congestion";
  const isMotor = device.id === "motor_conveyor";
  const isOn = device.current_state === "on";

  const currentColor = device.current_value?.color || "GREEN";
  const currentSpeed = device.current_value?.speed ?? (isOn ? 60 : 0);

  const handleTogglePower = async () => {
    setLoading(true);
    const nextState = isOn ? "off" : "on";
    let nextValue = device.current_value || {};

    if (isMotor) {
      nextValue = { speed: nextState === "on" ? 60 : 0, running: nextState === "on" };
    }
    await onControl(device.id, nextState, nextValue);
    setLoading(false);
  };

  const handleChangeLedColor = async (color: string) => {
    setLoading(true);
    const levelMap: Record<string, string> = {
      GREEN: "여유",
      ORANGE: "보통",
      RED: "혼잡",
    };
    await onControl(device.id, "on", {
      color,
      level: levelMap[color] || "여유",
      brightness: 100,
    });
    setLoading(false);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col justify-between hover:border-slate-300 transition">
      {/* 상단 라벨 및 상태 뱃지 */}
      <div>
        <div className="flex items-center justify-between gap-2 mb-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
            ACTUATOR · {device.kind}
          </span>
          <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${getStatusBadgeClass(device.current_state || undefined)}`}>
            {isOn ? "가동 중 (ON)" : "정지 (OFF)"}
          </span>
        </div>

        <h3 className="text-base font-bold text-slate-800">{device.name}</h3>
        <p className="text-xs text-slate-500 mt-0.5">
          {isLed && "지하철 객차 내 혼잡도 3색 LED 안내등"}
          {isMotor && "객차 창문 배경 흐름 시뮬레이션 컨베이어 모터"}
        </p>

        {/* 중앙 제어 인터페이스 */}
        <div className="my-5 p-3.5 bg-slate-50 border border-slate-200 rounded-lg">
          {isLed && (
            <div>
              <div className="flex items-center justify-between text-xs text-slate-600 mb-2 font-medium">
                <span>표시 색상 (혼잡도 단계)</span>
                <span className="font-bold text-slate-800">{currentColor}</span>
              </div>
              <div className="grid grid-cols-3 gap-1.5">
                <button
                  disabled={loading}
                  onClick={() => handleChangeLedColor("GREEN")}
                  className={`py-1.5 px-2 rounded-md text-xs font-bold border transition ${
                    isOn && currentColor === "GREEN"
                      ? "bg-emerald-600 text-white border-emerald-700 shadow-sm"
                      : "bg-white text-emerald-700 border-emerald-200 hover:bg-emerald-50"
                  }`}
                >
                  초록 (여유)
                </button>
                <button
                  disabled={loading}
                  onClick={() => handleChangeLedColor("ORANGE")}
                  className={`py-1.5 px-2 rounded-md text-xs font-bold border transition ${
                    isOn && currentColor === "ORANGE"
                      ? "bg-amber-500 text-white border-amber-600 shadow-sm"
                      : "bg-white text-amber-700 border-amber-200 hover:bg-amber-50"
                  }`}
                >
                  주황 (보통)
                </button>
                <button
                  disabled={loading}
                  onClick={() => handleChangeLedColor("RED")}
                  className={`py-1.5 px-2 rounded-md text-xs font-bold border transition ${
                    isOn && currentColor === "RED"
                      ? "bg-rose-600 text-white border-rose-700 shadow-sm"
                      : "bg-white text-rose-700 border-rose-200 hover:bg-rose-50"
                  }`}
                >
                  빨강 (혼잡)
                </button>
              </div>
            </div>
          )}

          {isMotor && (
            <div>
              <div className="flex items-center justify-between text-xs text-slate-600 mb-2 font-medium">
                <span>모터 회전 속도</span>
                <span className="font-bold text-slate-800">{currentSpeed} RPM</span>
              </div>
              <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-cyan-500 h-full transition-all duration-300 rounded-full"
                  style={{ width: isOn ? "75%" : "0%" }}
                />
              </div>
            </div>
          )}

          {/* 메인 전원 토글 버튼 */}
          <div className="mt-3 pt-3 border-t border-slate-200 flex items-center justify-between">
            <span className="text-xs text-slate-600 font-medium">전원 상태 제어</span>
            <button
              disabled={loading}
              onClick={handleTogglePower}
              className={`px-4 py-1.5 rounded-lg text-xs font-bold transition shadow-sm ${
                isOn
                  ? "bg-rose-600 hover:bg-rose-700 text-white"
                  : "bg-slate-800 hover:bg-slate-900 text-white"
              }`}
            >
              {loading ? "처리 중..." : isOn ? "전원 끄기" : "전원 켜기"}
            </button>
          </div>
        </div>
      </div>

      {/* 하단 메타 정보 */}
      <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
        <span>최근 조작: {device.last_actor || "user"}</span>
        <span suppressHydrationWarning>ID: {device.id}</span>
      </div>
    </div>
  );
};

export default ActuatorCard;
