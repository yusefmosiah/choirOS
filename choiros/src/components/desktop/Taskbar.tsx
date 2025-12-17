// Taskbar Component
import { useState, type FormEvent } from 'react';
import { useWindowStore } from '../../stores/windows';
import { APP_REGISTRY } from '../../lib/apps';
import './Taskbar.css';

export function Taskbar() {
    const [input, setInput] = useState('');
    const windows = useWindowStore((s) => s.windows);
    const focusWindow = useWindowStore((s) => s.focusWindow);
    const restoreWindow = useWindowStore((s) => s.restoreWindow);

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        if (!input.trim()) return;

        // For now, just log the command - agent integration comes in Phase 2
        console.log('[? Bar]', input.startsWith('?') ? 'Command:' : 'Intent:', input);
        setInput('');
    };

    // Get running (non-minimized or all) windows for the tray
    const runningWindows = Array.from(windows.values());

    return (
        <div className="taskbar">
            <button className="taskbar-menu-btn" type="button" title="Command Menu">
                ?
            </button>

            <form className="taskbar-input-form" onSubmit={handleSubmit}>
                <input
                    type="text"
                    className="taskbar-input"
                    placeholder="Ask anything or type ? for commands..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                />
            </form>

            <div className="taskbar-tray">
                {runningWindows.map((win) => {
                    const app = APP_REGISTRY[win.appId];
                    const IconComponent = app?.icon;

                    return (
                        <button
                            key={win.id}
                            className={`taskbar-app ${win.isFocused ? 'focused' : ''} ${win.isMinimized ? 'minimized' : ''}`}
                            onClick={() => win.isMinimized ? restoreWindow(win.id) : focusWindow(win.id)}
                            title={win.title}
                            type="button"
                        >
                            {IconComponent && <IconComponent size={18} />}
                        </button>
                    );
                })}
            </div>
        </div>
    );
}
