/**
 * useAgent - Hook for connecting to the ChoirOS agent via WebSocket.
 *
 * Provides:
 * - WebSocket connection management
 * - Message sending
 * - Response streaming
 */

import { useState, useCallback, useRef, useEffect } from 'react';

export interface AgentMessage {
    type: 'thinking' | 'tool_use' | 'tool_result' | 'text' | 'error' | 'done';
    content: unknown;
}

export interface UseAgentOptions {
    /** WebSocket URL for the supervisor agent endpoint */
    url?: string;
    /** Called when a message is received */
    onMessage?: (message: AgentMessage) => void;
}

export interface UseAgentReturn {
    /** Whether a prompt is currently being processed */
    isProcessing: boolean;
    /** Whether the WebSocket is connected */
    isConnected: boolean;
    /** Last error message */
    error: string | null;
    /** Send a prompt to the agent */
    sendPrompt: (prompt: string) => void;
    /** Current response messages */
    messages: AgentMessage[];
    /** Clear messages */
    clearMessages: () => void;
}

// Default WebSocket URL - supervisor runs on port 8001
const DEFAULT_WS_URL = 'ws://localhost:8001/agent';

export function useAgent(options: UseAgentOptions = {}): UseAgentReturn {
    const { url = DEFAULT_WS_URL, onMessage } = options;

    const [isConnected, setIsConnected] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [messages, setMessages] = useState<AgentMessage[]>([]);

    const wsRef = useRef<WebSocket | null>(null);
    const onMessageRef = useRef(onMessage);

    // Keep onMessage ref updated
    useEffect(() => {
        onMessageRef.current = onMessage;
    }, [onMessage]);

    const sendPrompt = useCallback((prompt: string) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
            setError('Not connected to agent');
            return;
        }

        setIsProcessing(true);
        setError(null);
        setMessages([]);

        wsRef.current.send(JSON.stringify({ prompt }));
    }, []);

    const clearMessages = useCallback(() => {
        setMessages([]);
    }, []);

    // Connect on mount with reconnection support
    useEffect(() => {
        let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
        let isMounted = true;

        const connect = () => {
            // Don't connect if already connected
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                return;
            }

            // Clear any existing connection
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }


            try {
                const ws = new WebSocket(url);

                ws.onopen = () => {
                    if (isMounted) {
                        setIsConnected(true);
                        setError(null);
                    }
                };

                ws.onclose = () => {
                    if (isMounted) {
                        setIsConnected(false);
                        setIsProcessing(false);
                    }
                    // Attempt to reconnect after 2 seconds
                    if (isMounted && !reconnectTimer) {
                        reconnectTimer = setTimeout(() => {
                            reconnectTimer = null;
                            connect();
                        }, 2000);
                    }
                };

                ws.onerror = () => {
                    // Silently handle errors - reconnection will be triggered by onclose
                };

                ws.onmessage = (event) => {
                    try {
                        const message: AgentMessage = JSON.parse(event.data);
                        setMessages((prev) => [...prev, message]);

                        // Call the external callback via ref
                        onMessageRef.current?.(message);

                        if (message.type === 'done' || message.type === 'error') {
                            setIsProcessing(false);
                        }
                    } catch {
                        console.error('Failed to parse agent message:', event.data);
                    }
                };

                wsRef.current = ws;
            } catch {
                // Schedule reconnect on error
                if (isMounted && !reconnectTimer) {
                    reconnectTimer = setTimeout(() => {
                        reconnectTimer = null;
                        connect();
                    }, 2000);
                }
            }
        };

        // Initial connection
        connect();

        return () => {
            isMounted = false;
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
            }
            if (wsRef.current) {
                wsRef.current.close();
                wsRef.current = null;
            }
        };
    }, [url]);

    return {
        isConnected,
        isProcessing,
        error,
        sendPrompt,
        messages,
        clearMessages,
    };
}
