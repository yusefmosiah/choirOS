import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Play, Square, Trash2 } from 'lucide-react';
import { authFetch } from '../../lib/auth';
import './Terminal.css';

const SUPERVISOR_BASE = import.meta.env.VITE_SUPERVISOR_URL || 'http://localhost:8001';

type OutputEntry = {
    id: string;
    kind: 'command' | 'stdout' | 'stderr' | 'system';
    text: string;
};

type ProcessEntry = {
    id: string;
    command: string;
};

function parseCommand(input: string): string[] {
    const tokens: string[] = [];
    let current = '';
    let quote: '"' | "'" | null = null;

    for (const char of input.trim()) {
        if (quote) {
            if (char === quote) {
                quote = null;
            } else {
                current += char;
            }
            continue;
        }
        if (char === '"' || char === "'") {
            quote = char;
            continue;
        }
        if (char === ' ' || char === '\t') {
            if (current) {
                tokens.push(current);
                current = '';
            }
            continue;
        }
        current += char;
    }
    if (current) {
        tokens.push(current);
    }
    return tokens;
}

export function Terminal() {
    const [command, setCommand] = useState('');
    const [output, setOutput] = useState<OutputEntry[]>([]);
    const [isRunning, setIsRunning] = useState(false);
    const [background, setBackground] = useState(false);
    const [processes, setProcesses] = useState<ProcessEntry[]>([]);
    const outputRef = useRef<HTMLDivElement | null>(null);

    const appendOutput = useCallback((entry: OutputEntry) => {
        setOutput((prev) => [...prev, entry]);
    }, []);

    const ensureSandbox = useCallback(async () => {
        const res = await authFetch(`${SUPERVISOR_BASE}/sandbox/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });
        if (!res.ok) {
            throw new Error('Failed to create sandbox');
        }
    }, []);

    const runCommand = useCallback(async () => {
        const trimmed = command.trim();
        if (!trimmed || isRunning) return;

        setIsRunning(true);
        appendOutput({ id: crypto.randomUUID(), kind: 'command', text: `$ ${trimmed}` });

        try {
            await ensureSandbox();
            const args = parseCommand(trimmed);
            if (args.length === 0) {
                setIsRunning(false);
                return;
            }

            const res = await authFetch(`${SUPERVISOR_BASE}/sandbox/exec`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    command: args,
                    background,
                }),
            });

            if (!res.ok) {
                appendOutput({ id: crypto.randomUUID(), kind: 'stderr', text: 'Exec failed' });
                return;
            }
            const data = await res.json();
            if (background && data.process_id) {
                setProcesses((prev) => [...prev, { id: data.process_id, command: trimmed }]);
                appendOutput({
                    id: crypto.randomUUID(),
                    kind: 'system',
                    text: `Started process ${data.process_id}`,
                });
                return;
            }

            if (data.stdout) {
                appendOutput({ id: crypto.randomUUID(), kind: 'stdout', text: data.stdout });
            }
            if (data.stderr) {
                appendOutput({ id: crypto.randomUUID(), kind: 'stderr', text: data.stderr });
            }
        } catch (error) {
            appendOutput({
                id: crypto.randomUUID(),
                kind: 'stderr',
                text: error instanceof Error ? error.message : 'Exec failed',
            });
        } finally {
            setIsRunning(false);
            setCommand('');
        }
    }, [appendOutput, background, command, ensureSandbox, isRunning]);

    const stopProcess = useCallback(async (processId: string) => {
        try {
            await authFetch(`${SUPERVISOR_BASE}/sandbox/process/stop`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ process_id: processId }),
            });
            setProcesses((prev) => prev.filter((proc) => proc.id !== processId));
            appendOutput({
                id: crypto.randomUUID(),
                kind: 'system',
                text: `Stopped process ${processId}`,
            });
        } catch (error) {
            appendOutput({
                id: crypto.randomUUID(),
                kind: 'stderr',
                text: error instanceof Error ? error.message : 'Stop failed',
            });
        }
    }, [appendOutput]);

    useEffect(() => {
        if (!outputRef.current) return;
        outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }, [output]);

    const runningCount = useMemo(() => processes.length, [processes.length]);

    return (
        <div className="terminal-panel">
            <div className="terminal-toolbar">
                <div className="terminal-status">
                    <span className="terminal-status-dot" />
                    <span>{runningCount} running</span>
                </div>
                <div className="terminal-actions">
                    <label className="terminal-checkbox">
                        <input
                            type="checkbox"
                            checked={background}
                            onChange={(e) => setBackground(e.target.checked)}
                        />
                        Background
                    </label>
                    <button
                        className="terminal-clear"
                        onClick={() => setOutput([])}
                        title="Clear output"
                    >
                        <Trash2 size={14} />
                        Clear
                    </button>
                </div>
            </div>

            <div className="terminal-output" ref={outputRef}>
                {output.map((entry) => (
                    <div key={entry.id} className={`terminal-line ${entry.kind}`}>
                        {entry.text}
                    </div>
                ))}
            </div>

            {processes.length > 0 && (
                <div className="terminal-processes">
                    {processes.map((proc) => (
                        <div key={proc.id} className="terminal-process">
                            <span className="terminal-process-id">{proc.id}</span>
                            <span className="terminal-process-command">{proc.command}</span>
                            <button
                                className="terminal-stop"
                                onClick={() => stopProcess(proc.id)}
                            >
                                <Square size={12} />
                                Stop
                            </button>
                        </div>
                    ))}
                </div>
            )}

            <div className="terminal-input">
                <input
                    type="text"
                    value={command}
                    onChange={(e) => setCommand(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && runCommand()}
                    placeholder="Enter command…"
                />
                <button onClick={runCommand} disabled={isRunning}>
                    <Play size={14} />
                    {isRunning ? 'Running…' : 'Run'}
                </button>
            </div>
        </div>
    );
}
