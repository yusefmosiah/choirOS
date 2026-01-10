// Desktop Component
import { useWindowStore } from '../../stores/windows';
import { APP_REGISTRY } from '../../lib/apps';
import { Icon } from './Icon';
import { Taskbar } from './Taskbar';
import { EventStream } from './EventStream';
import { WindowManager } from '../window/WindowManager';
import './Desktop.css';

const DESKTOP_ICONS = [
    { appId: 'files', label: 'Files' },
    { appId: 'writer', label: 'Writer' },
    { appId: 'terminal', label: 'Terminal' },
    { appId: 'mail', label: 'Mail' },
];

export function Desktop() {
    const openWindow = useWindowStore((s) => s.openWindow);

    const handleIconDoubleClick = (appId: string) => {
        openWindow(appId);
    };

    return (
        <div className="desktop">
            <div className="desktop-wallpaper" />

            <div className="desktop-icons">
                {DESKTOP_ICONS.map((icon) => {
                    const app = APP_REGISTRY[icon.appId];
                    if (!app) return null;

                    return (
                        <Icon
                            key={icon.appId}
                            icon={app.icon}
                            label={icon.label}
                            onDoubleClick={() => handleIconDoubleClick(icon.appId)}
                        />
                    );
                })}
            </div>

            <div className="desktop-windows">
                <WindowManager />
            </div>
            <EventStream />
            <Taskbar />
        </div>
    );
}
