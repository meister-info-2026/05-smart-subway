"use client";

import React from "react";
import ConnectionBadge from "@/components/dashboard/ConnectionBadge";
import { useSubwaySocket } from "@/hooks/useSubwaySocket";
import TrainCarView from "@/components/dashboard/TrainCarView";
import ActuatorCard from "@/components/dashboard/ActuatorCard";
import SensorCard from "@/components/dashboard/SensorCard";
import VisionLogList from "@/components/dashboard/VisionLogList";

export default function SubwayDashboardPage() {
  const {
    connected,
    devices,
    visionEvents,
    controlDevice,
    simulatePressureSeat,
    refreshData,
  } = useSubwaySocket();

  const ledDevice = devices["led_congestion"];
  const conveyorDevice = devices["motor_conveyor"];
  const cameraDevice = devices["cam_subway"];
  const pressureDevice = devices["sensor_seat_pressure"];

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900 pb-16">
      {/* 최상단 네비게이션 & 헤더 */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-sky-600 flex items-center justify-center text-white text-xl font-black shadow-sm">
              🚇
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg sm:text-xl font-black tracking-tight text-slate-900">
                  스마트 지하철 객차 혼잡도 & 임산부석 안내 관제 대시보드
                </h1>
                <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-slate-100 text-slate-600 border border-slate-200">
                  v1.0 Mockup
                </span>
              </div>
              <p className="text-xs text-slate-500">
                AI YOLOv8 실시간 인원 계측 · 3색 LED 안내등 · 임산부 배려석 압력 센싱 시스템
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => refreshData()}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-200 transition flex items-center gap-1.5"
            >
              🔄 새로고침
            </button>
            <ConnectionBadge connected={connected} />
          </div>
        </div>
      </header>

      {/* 대시보드 메인 본문 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        {/* 1. 지하철 객차 뷰 & 임산부석 실시간 시각화 */}
        <TrainCarView
          camDevice={cameraDevice}
          ledDevice={ledDevice}
          pressureDevice={pressureDevice}
          conveyorDevice={conveyorDevice}
          onSimulateSeat={(occupied) => simulatePressureSeat(occupied)}
        />

        {/* 2. 디바이스 제어 및 센서 카드 그리드 */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-bold text-slate-800">
              IoT 디바이스 및 센서 제어 패널
            </h2>
            <span className="text-xs text-slate-500 font-medium">
              Mock Provider (Windows PC 가상 시뮬레이션 동작 중)
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {ledDevice && (
              <ActuatorCard device={ledDevice} onControl={controlDevice} />
            )}
            {conveyorDevice && (
              <ActuatorCard device={conveyorDevice} onControl={controlDevice} />
            )}
            {pressureDevice && (
              <SensorCard
                device={pressureDevice}
                onSimulateSeat={(occupied, val) => simulatePressureSeat(occupied, val)}
              />
            )}
            {cameraDevice && <SensorCard device={cameraDevice} />}
          </div>
        </div>

        {/* 3. 실시간 비전 감지 피드 로그 */}
        <VisionLogList events={visionEvents} />

        {/* 시스템 안내 바 */}
        <footer className="mt-8 text-center text-xs text-slate-400 py-4 border-t border-slate-200">
          AI 기반 지하철 객차 혼잡도 실시간 분석 및 임산부석 안내 스마트 시스템 · 1차 완성 (Windows PC Mockup 베이스라인)
        </footer>
      </main>
    </div>
  );
}
