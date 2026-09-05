/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface DeviceInfo {
  id: string;
  name: string;
  kind: string;
  desired_state?: string | null;
  current_state?: string | null;
  desired_value?: Record<string, any> | null;
  current_value?: Record<string, any> | null;
  last_actor?: string;
  updated_at?: string;
}

export interface VisionEventItem {
  event_type: string;
  detected: boolean;
  count: number;
  confidence?: number | null;
  congestion_level: string;
  led_color: string;
  created_at?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";

export function useSubwaySocket() {
  const [connected, setConnected] = useState(false);
  const [devices, setDevices] = useState<Record<string, DeviceInfo>>({});
  const [visionEvents, setVisionEvents] = useState<VisionEventItem[]>([]);
  const [lastMessageTime, setLastMessageTime] = useState<string>("");

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 초기 REST API 폴링으로 디바이스 목록 및 이전 이벤트 불러오기
  const fetchInitialData = useCallback(async () => {
    try {
      const devRes = await fetch(`${API_BASE}/api/v1/devices`);
      if (devRes.ok) {
        const json = await devRes.json();
        const map: Record<string, DeviceInfo> = {};
        (json.data || []).forEach((d: DeviceInfo) => {
          map[d.id] = d;
        });
        setDevices((prev) => ({ ...prev, ...map }));
      }

      const visionRes = await fetch(`${API_BASE}/api/v1/vision/events?limit=15`);
      if (visionRes.ok) {
        const vJson = await visionRes.json();
        setVisionEvents(vJson.data || []);
      }
    } catch (err) {
      console.warn("Initial data fetch warning (backend might be starting):", err);
    }
  }, []);

  const connectWebSocketRef = useRef<() => void>(() => {});

  const connectWebSocket = useCallback(() => {
    if (
      wsRef.current &&
      (wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    try {
      const socket = new WebSocket(WS_URL);
      wsRef.current = socket;

      socket.onopen = () => {
        console.log("[WS] Connected to Subway Backend");
        setConnected(true);
      };

      socket.onmessage = (event) => {
        setLastMessageTime(new Date().toLocaleTimeString());
        try {
          const payload = JSON.parse(event.data);

          if (payload.type === "initial_state" && Array.isArray(payload.devices)) {
            const map: Record<string, DeviceInfo> = {};
            payload.devices.forEach((d: DeviceInfo) => {
              map[d.id] = d;
            });
            setDevices((prev) => ({ ...prev, ...map }));
          } else if (
            payload.type === "device_updated" ||
            payload.type === "device_state_reported"
          ) {
            const dev = payload.device;
            if (dev && dev.id) {
              setDevices((prev) => ({ ...prev, [dev.id]: dev }));
            }
          } else if (payload.type === "pressure_seat_updated") {
            const dev = payload.device;
            if (dev && dev.id) {
              setDevices((prev) => ({ ...prev, [dev.id]: dev }));
            }
          } else if (payload.type === "vision_event") {
            const ev = payload.event;
            if (ev) {
              setVisionEvents((prev) => [ev, ...prev.slice(0, 19)]);
            }
            setDevices((prev) => {
              const updated = { ...prev };
              if (updated["cam_subway"]) {
                updated["cam_subway"] = {
                  ...updated["cam_subway"],
                  current_value: {
                    ...(updated["cam_subway"].current_value || {}),
                    person_count: payload.person_count,
                    congestion: payload.congestion_level,
                  },
                };
              }
              if (updated["led_congestion"]) {
                updated["led_congestion"] = {
                  ...updated["led_congestion"],
                  current_state: "on",
                  current_value: {
                    ...(updated["led_congestion"].current_value || {}),
                    color: payload.led_color,
                    level: payload.congestion_level,
                    brightness: 100,
                  },
                };
              }
              return updated;
            });
          }
        } catch (parseErr) {
          console.error("[WS] Message parse error:", parseErr);
        }
      };

      socket.onerror = (err) => {
        console.warn("[WS] Socket error:", err);
      };

      socket.onclose = () => {
        console.log("[WS] Disconnected. Reconnecting in 3s...");
        setConnected(false);
        wsRef.current = null;
        if (!reconnectTimerRef.current) {
          reconnectTimerRef.current = setTimeout(() => {
            reconnectTimerRef.current = null;
            connectWebSocketRef.current();
          }, 3000);
        }
      };
    } catch (err) {
      console.warn("[WS] Connection initiation error:", err);
      if (!reconnectTimerRef.current) {
        reconnectTimerRef.current = setTimeout(() => {
          reconnectTimerRef.current = null;
          connectWebSocketRef.current();
        }, 3000);
      }
    }
  }, []);

  useEffect(() => {
    connectWebSocketRef.current = connectWebSocket;
  }, [connectWebSocket]);

  useEffect(() => {
    void fetchInitialData();
    connectWebSocket();

    return () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [fetchInitialData, connectWebSocket]);

  // 디바이스 제어 명령 전송 함수
  const controlDevice = async (
    deviceId: string,
    desiredState: string,
    desiredValue?: unknown,
    operator: string = "user"
  ) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/devices/${deviceId}/control`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          desired_state: desiredState,
          desired_value: desiredValue,
          operator,
        }),
      });
      if (res.ok) {
        const json = await res.json();
        const updated = json.data;
        if (updated) {
          setDevices((prev) => ({ ...prev, [deviceId]: updated }));
        }
        return true;
      }
    } catch (err) {
      console.error(`Failed to control device ${deviceId}:`, err);
    }
    return false;
  };

  // 임산부석 압력센서 시뮬레이션 명령 함수
  const simulatePressureSeat = async (occupied: boolean, pressureVal?: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/devices/sensor/pressure-simulate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          occupied,
          pressure_val: pressureVal,
        }),
      });
      if (res.ok) {
        const json = await res.json();
        const updated = json.data;
        if (updated) {
          setDevices((prev) => ({ ...prev, [updated.id]: updated }));
        }
        return true;
      }
    } catch (err) {
      console.error("Failed to simulate pressure seat:", err);
    }
    return false;
  };

  return {
    connected,
    devices,
    visionEvents,
    lastMessageTime,
    controlDevice,
    simulatePressureSeat,
    refreshData: fetchInitialData,
  };
}
