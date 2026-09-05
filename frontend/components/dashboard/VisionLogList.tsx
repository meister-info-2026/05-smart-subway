"use client";

import React from "react";
import { VisionEventItem } from "@/hooks/useSubwaySocket";

interface VisionLogListProps {
  events: VisionEventItem[];
}

export const VisionLogList: React.FC<VisionLogListProps> = ({ events }) => {
  const getBadgeStyle = (level: string) => {
    switch (level) {
      case "혼잡":
        return "bg-rose-100 text-rose-800 border-rose-200";
      case "보통":
        return "bg-amber-100 text-amber-800 border-amber-200";
      default:
        return "bg-emerald-100 text-emerald-800 border-emerald-200";
    }
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
        <div>
          <h3 className="text-base font-bold text-slate-800">
            YOLO 영상인식 실시간 감지 로그 피드
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            객차 내 승객 탐지 및 혼잡도 트리거 실행 기록
          </p>
        </div>
        <span className="text-xs px-2.5 py-1 bg-slate-100 text-slate-600 rounded-full font-semibold">
          최근 {events.length}건
        </span>
      </div>

      {events.length === 0 ? (
        <div className="py-8 text-center text-slate-400 text-xs">
          수신된 영상인식 이벤트가 아직 없습니다. (vision/main.py 실행 대기 중)
        </div>
      ) : (
        <div className="divide-y divide-slate-100 max-h-80 overflow-y-auto pr-1">
          {events.map((ev, idx) => (
            <div key={idx} className="py-2.5 flex items-center justify-between text-xs hover:bg-slate-50/80 px-2 rounded-lg transition">
              <div className="flex items-center gap-3">
                <span className="font-mono text-slate-400 text-[11px]" suppressHydrationWarning>
                  {ev.created_at ? new Date(ev.created_at).toLocaleTimeString() : "방금"}
                </span>
                <span className="font-semibold text-slate-700">
                  {ev.event_type === "person_count" ? "승객 카운트" : ev.event_type}
                </span>
                <span className="text-slate-600 font-medium">
                  <strong>{ev.count}</strong> 명 감지
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-[11px] font-bold border ${getBadgeStyle(ev.congestion_level)}`}>
                  {ev.congestion_level}
                </span>
                <span className="text-[11px] text-slate-400">
                  LED: <strong className="text-slate-700">{ev.led_color}</strong>
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default VisionLogList;
