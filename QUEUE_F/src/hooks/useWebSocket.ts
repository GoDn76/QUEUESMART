import { useEffect, useRef } from 'react';

type WebSocketEvent = {
  type: 'TOKEN_JOINED' | 'QUEUE_ADVANCED' | 'TOKEN_COMPLETED' | 'TOKEN_SKIPPED' | 'TOKEN_ESCALATED' | 'YOUR_TURN' | 'TOKEN_NEAR';
  payload: any;
};

export function useWebSocket(url: string, onMessage: (event: WebSocketEvent) => void) {
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    const connect = () => {
      ws.current = new WebSocket(url);

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketEvent;
          onMessage(data);
        } catch (e) {
          console.error("Failed to parse WebSocket message", e);
        }
      };

      ws.current.onclose = () => {
        // Simple exponential backoff or standard reconnect could go here
        setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [url, onMessage]);

  return ws.current;
}
