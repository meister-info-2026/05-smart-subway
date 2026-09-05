"use client";

import React, { useState } from "react";
import { DeviceInfo } from "@/hooks/useSubwaySocket";
import { getStatusBadgeClass } from "@/components/dashboard/statusColor";

interface SensorCardProps {
  device: DeviceInfo;
  onSimulateSeat?: (occupied: boolean, pressureVal?: number) => Promise<boolean>;
}

export const SensorCard: React.FC<SensorCardProps> = ({ device, onSimulateSeat }) => {
  const [loading, setLoading] = useState(false);

  const isPressure = device.id === "sensor_seat_pressure";
  const isCamera = device.id === "cam_subway";

  const isOccupied = device.current_value?.occupied ?? false;
  const pressureVal = device.current_value?.pressure_val ?? 0.0;
  const personCount = device.current_value?.person_count ?? 0;
  const congestion = device.current_value?.congestion ?? "여유";

  const handleSeatToggle = async (occupied: boolean) => {
    if (!onSimulateSeat) return;
    setLoading(true);
    await onSimulateSeat(occupied, occupied ? 71.5 : 0.0);
    setLoading(false);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col justify-between hover:border-slate-300 transition">
      <div>
        {/* 상단 메타 라벨 */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
            SENSOR · {device.kind}
          </span>
          <span
            className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${getStatusBadgeClass(
              isPressure ? (isOccupied ? "alert" : "info") : "info"
            )}`}
          >
            {isPressure ? (isOccupied ? "좌석 점유됨" : "좌석 비어있음") : "카메라 감지 중"}
          </span>
        </div>

        <h3 className="text-base font-bold text-slate-800">{device.name}</h3>
        <p className="text-xs text-slate-500 mt-0.5">
          {isPressure && "임산부 배려석 방석 하부 압력 감지 센서"}
          {isCamera && "객차 상단 Pi Camera 3 YOLO 인원수 분석 센서"}
        </p>

        {/* 중앙 큰 수치 표시 */}
        <div className="my-5 p-4 bg-slate-50 border border-slate-200 rounded-lg text-center">
          {isPressure && (
            <div>
              <div className="text-3xl font-extrabold text-slate-800">
                {pressureVal.toFixed(1)} <span className="text-base font-medium text-slate-500">kg</span>
              </div>
              <div className="mt-1 text-xs text-slate-500 font-medium">
                {isOccupied ? "성인 승객 착석 감지됨" : "압력 미감지 (대기 상태)"}
              </div>

              {/* 시뮬레이션 버튼 */}
              {onSimulateSeat && (
                <div className="mt-3 pt-3 border-t border-slate-200 flex gap-2 justify-center">
                  <button
                    disabled={loading}
                    onClick={() => handleSeatToggle(true)}
                    className="px-3 py-1.5 rounded-md text-xs font-bold bg-pink-50 text-pink-700 border border-pink-200 hover:bg-pink-100 transition"
                  >
                    착석 시뮬레이션
                  </button>
                  <button
                    disabled={loading}
                    onClick={() => handleSeatToggle(false)}
                    className="px-3 py-1.5 rounded-md text-xs font-bold bg-slate-100 text-slate-700 border border-slate-200 hover:bg-slate-200 transition"
                  >
                    기립 (초기화)
                  </button>
                </div>
              )}
            </div>
          )}

          {isCamera && (
            <div>
              <div className="text-3xl font-extrabold text-slate-800">
                {personCount} <span className="text-base font-medium text-slate-500">명</span>
              </div>
              <div className="mt-1 text-xs text-slate-500 font-medium">
                현재 판별 혼잡도: <strong className="text-slate-800">{congestion}</strong>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 하단 갱신 정보 */}
      <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
        <span suppressHydrationWarning>
          갱신: {device.updated_at ? new Date(device.updated_at).toLocaleTimeString() : "-"}
        </span>
        <span suppressHydrationWarning>ID: {device.id}</span>
      </div>
    </div>
  );
};

export default SensorCard;
