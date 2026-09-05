"use client";

import React from "react";
import { DeviceInfo } from "@/hooks/useSubwaySocket";

interface TrainCarViewProps {
  camDevice?: DeviceInfo;
  ledDevice?: DeviceInfo;
  pressureDevice?: DeviceInfo;
  conveyorDevice?: DeviceInfo;
  onSimulateSeat?: (occupied: boolean) => void;
}

export const TrainCarView: React.FC<TrainCarViewProps> = ({
  camDevice,
  ledDevice,
  pressureDevice,
  conveyorDevice,
  onSimulateSeat,
}) => {
  const personCount = camDevice?.current_value?.person_count ?? 0;
  const congestionLevel = camDevice?.current_value?.congestion ?? "여유";
  const ledColor = ledDevice?.current_value?.color ?? "GREEN";
  const isSeatOccupied = pressureDevice?.current_value?.occupied ?? false;
  const pressureVal = pressureDevice?.current_value?.pressure_val ?? 0.0;
  const isConveyorRunning = conveyorDevice?.current_state === "on";

  // 혼잡도에 따른 뱃지 및 프로그레스 바 스타일
  const getCongestionStyles = () => {
    switch (congestionLevel) {
      case "혼잡":
        return {
          barClass: "bg-rose-500",
          badgeClass: "bg-rose-100 text-rose-800 border-rose-300",
          progressPct: "90%",
          desc: "객차 내 인원이 많아 탑승 시 혼잡합니다.",
        };
      case "보통":
        return {
          barClass: "bg-amber-500",
          badgeClass: "bg-amber-100 text-amber-800 border-amber-300",
          progressPct: "55%",
          desc: "적정 인원이 탑승 중입니다.",
        };
      default:
        return {
          barClass: "bg-emerald-500",
          badgeClass: "bg-emerald-100 text-emerald-800 border-emerald-300",
          progressPct: "25%",
          desc: "좌석 및 통로 여유 공간이 충분합니다.",
        };
    }
  };

  const { barClass, badgeClass, progressPct, desc } = getCongestionStyles();

  // LED 안내등 시각화 색상
  const getLedDotClass = () => {
    if (ledColor === "RED") return "bg-rose-500 shadow-rose-500/50";
    if (ledColor === "ORANGE") return "bg-amber-500 shadow-amber-500/50";
    return "bg-emerald-500 shadow-emerald-500/50";
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm mb-6">
      {/* 상단 타이틀 & 열차 주행 상태 */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-100">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-md text-xs font-bold bg-sky-100 text-sky-800 border border-sky-200">
              수도권 2호선
            </span>
            <h2 className="text-xl font-bold text-slate-800">지하철 객차 실시간 모니터링 뷰</h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            객차 1호차 AI 영상인식 실시간 분석 및 임산부석 압력센서 상태
          </p>
        </div>

        {/* 컨베이어(모터) 주행 인디케이터 */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs">
          <span
            className={`w-2.5 h-2.5 rounded-full ${
              isConveyorRunning ? "bg-cyan-500 animate-ping" : "bg-slate-300"
            }`}
          />
          <span className="font-semibold text-slate-700">
            {isConveyorRunning ? "열차 주행 시뮬레이션 중 (모터 ON)" : "열차 정차 중 (모터 OFF)"}
          </span>
        </div>
      </div>

      {/* 2칸 객차 그래픽 뷰 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mt-6">
        {/* 1호차 (활성 모니터링 객차) */}
        <div className="lg:col-span-8 bg-gradient-to-br from-slate-50 to-white border-2 border-sky-300 rounded-xl p-5 shadow-sm relative overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <div className="flex items-center gap-2">
              <span className="px-2 py-1 bg-sky-600 text-white rounded font-bold text-xs tracking-wider">
                1호차
              </span>
              <span className="text-xs font-semibold text-sky-700">실시간 AI 센싱 중</span>
            </div>

            {/* 물리 LED 안내등 미러링 표시 */}
            <div className="flex items-center gap-2 bg-slate-900 text-white px-3 py-1 rounded-full text-xs shadow-inner">
              <span className="text-slate-400 font-mono text-[11px]">LED STATUS:</span>
              <span className={`w-3 h-3 rounded-full shadow-lg ${getLedDotClass()}`} />
              <span className="font-bold">{ledColor}</span>
            </div>
          </div>

          {/* 혼잡도 메트릭 */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5">
            <div className="bg-white p-3.5 rounded-lg border border-slate-200">
              <span className="text-xs text-slate-500 font-medium">탐지 승객 수</span>
              <div className="text-3xl font-extrabold text-slate-800 mt-1">
                {personCount} <span className="text-sm font-normal text-slate-500">명</span>
              </div>
            </div>

            <div className="bg-white p-3.5 rounded-lg border border-slate-200">
              <span className="text-xs text-slate-500 font-medium">혼잡도 상태</span>
              <div className="mt-1 flex items-center gap-2">
                <span className={`px-2.5 py-0.5 rounded-md text-sm font-bold border ${badgeClass}`}>
                  {congestionLevel}
                </span>
              </div>
              <span className="text-[11px] text-slate-400 mt-1 block truncate">{desc}</span>
            </div>

            <div className="bg-white p-3.5 rounded-lg border border-slate-200">
              <span className="text-xs text-slate-500 font-medium">임산부 배려석 현황</span>
              <div className="mt-1 flex items-center gap-2">
                <span
                  className={`px-2.5 py-0.5 rounded-md text-sm font-bold border ${
                    isSeatOccupied
                      ? "bg-pink-100 text-pink-800 border-pink-300"
                      : "bg-emerald-100 text-emerald-800 border-emerald-300"
                  }`}
                >
                  {isSeatOccupied ? "착석 중 (점유)" : "비어 있음 (안내)"}
                </span>
              </div>
              <span className="text-[11px] text-slate-400 mt-1 block">
                압력 수치: {pressureVal.toFixed(1)} kg
              </span>
            </div>
          </div>

          {/* 혼잡도 프로그레스 게이지 */}
          <div className="mb-6">
            <div className="flex justify-between text-xs text-slate-600 mb-1.5 font-medium">
              <span>혼잡도 게이지</span>
              <span>
                기준: 여유(0~2명) · 보통(3~5명) · 혼잡(6명 이상)
              </span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
              <div
                className={`h-full transition-all duration-500 rounded-full ${barClass}`}
                style={{ width: progressPct }}
              />
            </div>
          </div>

          {/* 임산부석 실시간 시각화 존 */}
          <div
            className={`p-4 rounded-xl border transition-all duration-300 ${
              isSeatOccupied
                ? "bg-pink-50/70 border-pink-300 shadow-sm"
                : "bg-emerald-50/70 border-emerald-200"
            }`}
          >
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-3">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-lg ${
                    isSeatOccupied
                      ? "bg-pink-500 text-white shadow-pink-200 shadow-md"
                      : "bg-emerald-500 text-white shadow-emerald-200 shadow-md"
                  }`}
                >
                  {isSeatOccupied ? "🤰" : "✨"}
                </div>
                <div>
                  <h4 className="font-bold text-slate-800 text-sm flex items-center gap-2">
                    핑크라이트 임산부 배려석
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        isSeatOccupied
                          ? "bg-pink-200 text-pink-800"
                          : "bg-emerald-200 text-emerald-800"
                      }`}
                    >
                      {isSeatOccupied ? "현재 착석 중" : "착석 가능"}
                    </span>
                  </h4>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {isSeatOccupied
                      ? `압력센서 감지 완료 (${pressureVal.toFixed(1)} kg) — 다음 역 안내 시스템과 연동`
                      : "좌석이 비어있습니다. 임산부 승객 탑승 시 양보해 주세요."}
                  </p>
                </div>
              </div>

              {/* 빠른 시뮬레이션 토글 버튼 */}
              {onSimulateSeat && (
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => onSimulateSeat(true)}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition ${
                      isSeatOccupied
                        ? "bg-pink-600 text-white border-pink-600 shadow-sm"
                        : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    착석 시뮬레이션
                  </button>
                  <button
                    onClick={() => onSimulateSeat(false)}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-lg border transition ${
                      !isSeatOccupied
                        ? "bg-emerald-600 text-white border-emerald-600 shadow-sm"
                        : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
                    }`}
                  >
                    기립 (비움)
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 2호차 (인접 객차 정보 뷰) */}
        <div className="lg:col-span-4 bg-slate-50 border border-slate-200 rounded-xl p-5 flex flex-col justify-between">
          <div>
            <div className="flex justify-between items-start mb-3">
              <span className="px-2 py-1 bg-slate-600 text-white rounded font-bold text-xs tracking-wider">
                2호차
              </span>
              <span className="text-xs font-medium text-slate-500">인접 객차</span>
            </div>
            <h3 className="font-bold text-slate-800 text-base">다음 객차 혼잡도 안내</h3>
            <p className="text-xs text-slate-500 mt-1">
              플랫폼 및 환승 승객을 위한 인접 객차 여유 좌석 안내
            </p>

            <div className="mt-4 space-y-3">
              <div className="bg-white p-3 rounded-lg border border-slate-200 flex justify-between items-center">
                <span className="text-xs text-slate-600 font-medium">인접 객차 탑승 인원</span>
                <span className="text-base font-bold text-slate-800">2 명</span>
              </div>
              <div className="bg-white p-3 rounded-lg border border-slate-200 flex justify-between items-center">
                <span className="text-xs text-slate-600 font-medium">인접 객차 혼잡도</span>
                <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                  여유
                </span>
              </div>
              <div className="bg-white p-3 rounded-lg border border-slate-200 flex justify-between items-center">
                <span className="text-xs text-slate-600 font-medium">임산부석 점유 여부</span>
                <span className="px-2 py-0.5 rounded text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-300">
                  비어 있음
                </span>
              </div>
            </div>
          </div>

          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-[11px] text-blue-700 leading-relaxed">
            💡 <strong>탑승 안내 팁:</strong> 1호차가 혼잡할 경우 승강장 안내 전광판을 통해 2호차로 분산 탑승을 유도합니다.
          </div>
        </div>
      </div>
    </div>
  );
};

export default TrainCarView;
