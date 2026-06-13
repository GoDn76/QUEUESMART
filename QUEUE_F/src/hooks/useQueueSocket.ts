import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

type RoomType = "counter" | "display" | "user" | "organization";
export type SocketStatus = "connecting" | "connected" | "reconnecting" | "disconnected";

/**
 * Resolves the WebSocket URL dynamically based on the VITE_API_URL.
 * Replaces http/https with ws/wss and strips the trailing /api/v1 path.
 */
const resolveWsUrl = (roomType: RoomType, roomId: string): string => {
  const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
  // Strip the /api/v1 segment from the URL
  const baseUrl = apiUrl.replace(/\/api\/v1\/?$/, "");
  // Replace HTTP(s) protocol with WS(s)
  const wsBase = baseUrl.startsWith("https")
    ? baseUrl.replace("https", "wss")
    : baseUrl.replace("http", "ws");
    
  return `${wsBase}/ws/${roomType}/${roomId}`;
};

interface SocketMessage {
  event_type: string;
  payload?: any;
  [key: string]: any;
}

export const useQueueSocket = (roomType: RoomType, roomId: string | null | undefined) => {
  const queryClient = useQueryClient();
  const socketRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<SocketStatus>("disconnected");
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intentionallyClosed = useRef<boolean>(false);
  const reconnectAttempts = useRef<number>(0);

  useEffect(() => {
    if (!roomId) return;
    
    // Reset flags on new connection instance
    intentionallyClosed.current = false;
    reconnectAttempts.current = 0;

    const connect = () => {
      setStatus(socketRef.current ? "reconnecting" : "connecting");
      
      const wsUrl = resolveWsUrl(roomType, roomId);
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
        reconnectAttempts.current = 0; // reset attempts
        if (import.meta.env.DEV) {
          console.log(`[WebSocket] Connected to ${roomType}: ${roomId}`);
        }
      };

      ws.onmessage = (event) => {
        try {
          const data: SocketMessage = JSON.parse(event.data);
          if (!data?.event_type) return;

          if (import.meta.env.DEV) {
            console.log(`[WebSocket] Event Received:`, data.event_type);
          }

          // Events that mutate queue order or token state
          const refreshEvents = [
            "TOKEN_JOINED",
            "QUEUE_ADVANCED",
            "TOKEN_COMPLETED",
            "TOKEN_SKIPPED",
            "TOKEN_ESCALATED"
          ];

          // Trigger TanStack Query to instantly refetch the current queue contexts
          if (refreshEvents.includes(data.event_type)) {
            queryClient.invalidateQueries({ queryKey: ["current-queue", roomId] });
            queryClient.invalidateQueries({ queryKey: ["current-serving", roomId] });
            queryClient.invalidateQueries({ queryKey: ["display-board", roomId] });
            queryClient.invalidateQueries({ queryKey: ["analytics-summary"] });
          }
        } catch (error) {
          // Gracefully ignore parse errors
          return;
        }
      };

      ws.onclose = () => {
        setStatus("disconnected");
        
        if (intentionallyClosed.current) return;

        // Exponential Backoff (3s, 6s, 12s, max 30s)
        const backoffBase = 3000;
        const delay = Math.min(backoffBase * Math.pow(2, reconnectAttempts.current), 30000);
        
        if (import.meta.env.DEV) {
          console.warn(`[WebSocket] Disconnected. Attempting reconnect in ${delay/1000}s...`);
        }
        
        reconnectAttempts.current += 1;
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      };

      ws.onerror = (error) => {
        if (import.meta.env.DEV) {
          console.error("[WebSocket] Error occurred:", error);
        }
        ws.close();
      };
    };

    connect();

    return () => {
      intentionallyClosed.current = true;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        // Prevent onclose logic from firing during normal cleanup
        socketRef.current.onclose = null;
        socketRef.current.close();
        setStatus("disconnected");
      }
    };
  }, [roomType, roomId, queryClient]);

  return { 
    isConnected: status === "connected",
    status,
    socket: socketRef.current
  };
};
