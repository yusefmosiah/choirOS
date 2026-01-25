// Window Manager Component
import { useWindowStore } from '../../stores/windows';
import { Window } from './Window';
import { Writer } from '../apps/Writer';
import { Files } from '../apps/Files';
import { MailApp } from '../apps/Mail';
import { GitPanel } from '../apps/GitPanel';
import { AuthApp } from '../apps/Auth';
import { Terminal } from '../apps/Terminal';
import { Auditor } from '../apps/Auditor';
import { ContextHeatmap } from '../apps/ContextHeatmap';
import { ContextMindMap } from '../apps/ContextMindMap';

// App component mapping
const APP_COMPONENTS: Record<string, React.ComponentType<Record<string, unknown>>> = {
    writer: Writer,
    files: Files,
    mail: MailApp,
    git: GitPanel,
    auth: AuthApp,
    terminal: Terminal,
    auditor: Auditor,
    contextHeatmap: ContextHeatmap,
    contextMindMap: ContextMindMap,
};

// Placeholder component for apps not yet implemented
function PlaceholderApp({ appId }: { appId: string }) {
    return (
        <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: 'var(--text-secondary)',
            fontSize: '14px',
        }}>
            {appId} app coming in a later phase
        </div>
    );
}

export function WindowManager() {
    const windows = useWindowStore((s) => s.windows);

    return (
        <>
            {Array.from(windows.values())
                .filter((win) => !win.isMinimized)
                .map((windowState) => {
                    const AppComponent = APP_COMPONENTS[windowState.appId];
                    const appProps = (windowState.props ?? {}) as Record<string, unknown>;

                    return (
                        <Window key={windowState.id} windowState={windowState}>
                            {AppComponent ? (
                                <AppComponent {...appProps} />
                            ) : (
                                <PlaceholderApp appId={windowState.appId} />
                            )}
                        </Window>
                    );
                })}
        </>
    );
}
