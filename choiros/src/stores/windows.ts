// Window Manager Store
import { create } from 'zustand';

export interface WindowState {
    id: string;
    appId: string;
    title: string;
    position: { x: number; y: number };
    size: { width: number; height: number };
    zIndex: number;
    isMinimized: boolean;
    isMaximized: boolean;
    isFocused: boolean;
    // Optional props to pass to the app component
    props?: Record<string, unknown>;
}

interface WindowManagerState {
    windows: Map<string, WindowState>;
    focusedWindowId: string | null;
    nextZIndex: number;
}

interface WindowStore extends WindowManagerState {
    openWindow: (appId: string, props?: { title?: string; artifactId?: string }) => string;
    closeWindow: (id: string) => void;
    focusWindow: (id: string) => void;
    minimizeWindow: (id: string) => void;
    maximizeWindow: (id: string) => void;
    restoreWindow: (id: string) => void;
    moveWindow: (id: string, x: number, y: number) => void;
    resizeWindow: (id: string, width: number, height: number) => void;
    getWindow: (id: string) => WindowState | undefined;
}

// Default window sizes by app
const DEFAULT_SIZES: Record<string, { width: number; height: number }> = {
    writer: { width: 800, height: 600 },
    files: { width: 700, height: 500 },
    terminal: { width: 700, height: 450 },
    git: { width: 500, height: 600 },
};

// App titles
const APP_TITLES: Record<string, string> = {
    writer: 'Writer',
    files: 'Files',
    terminal: 'Terminal',
    git: 'Git',
};

export const useWindowStore = create<WindowStore>((set, get) => ({
    windows: new Map(),
    focusedWindowId: null,
    nextZIndex: 1,

    openWindow: (appId, props = {}) => {
        const id = crypto.randomUUID();
        const { nextZIndex, windows } = get();

        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight - 48; // Account for taskbar

        // Determine size factors based on viewport
        let widthFactor: number;
        let heightFactor: number;

        if (viewportWidth < 500) {
            // Phone: nearly full width, tall height
            widthFactor = 0.95;
            heightFactor = 0.92;
        } else if (viewportWidth < 900) {
            // Tablet: leave visible margins
            widthFactor = 0.70;
            heightFactor = 0.65;
        } else {
            // Desktop: use app defaults (factor of 1 means use default, capped at viewport)
            widthFactor = 1;
            heightFactor = 1;
        }

        const defaultSize = DEFAULT_SIZES[appId] || { width: 600, height: 400 };

        // Calculate size: on mobile use viewport-based sizing, on desktop use defaults (capped)
        const isMobile = viewportWidth < 900;
        const size = isMobile
            ? {
                width: viewportWidth * widthFactor,
                height: viewportHeight * heightFactor,
            }
            : {
                width: Math.min(defaultSize.width, viewportWidth * widthFactor),
                height: Math.min(defaultSize.height, viewportHeight * heightFactor),
            };

        // Position: center horizontally, slight offset from top
        // Cascade multiple windows slightly
        const cascadeOffset = (windows.size % 5) * 20;
        const position = {
            x: Math.max(10, (viewportWidth - size.width) / 2 + cascadeOffset),
            y: Math.max(10, 30 + cascadeOffset),
        };

        const windowState: WindowState = {
            id,
            appId,
            title: props.title || APP_TITLES[appId] || appId,
            position,
            size,
            zIndex: nextZIndex,
            isMinimized: false,
            isMaximized: false,
            isFocused: true,
            props: props.artifactId ? { artifactId: props.artifactId } : undefined,
        };
        // Unfocus all other windows
        const newWindows = new Map(windows);
        newWindows.forEach((w) => {
            w.isFocused = false;
        });
        newWindows.set(id, windowState);

        set({
            windows: newWindows,
            focusedWindowId: id,
            nextZIndex: nextZIndex + 1,
        });

        return id;
    },

    closeWindow: (id) => {
        const { windows, focusedWindowId } = get();
        const newWindows = new Map(windows);
        newWindows.delete(id);

        // Focus the next highest z-index window if we closed the focused one
        let newFocusedId: string | null = null;
        if (focusedWindowId === id && newWindows.size > 0) {
            let maxZ = -1;
            newWindows.forEach((w) => {
                if (w.zIndex > maxZ && !w.isMinimized) {
                    maxZ = w.zIndex;
                    newFocusedId = w.id;
                }
            });
            if (newFocusedId) {
                const focusedWindow = newWindows.get(newFocusedId);
                if (focusedWindow) {
                    focusedWindow.isFocused = true;
                }
            }
        }

        set({
            windows: newWindows,
            focusedWindowId: focusedWindowId === id ? newFocusedId : focusedWindowId,
        });
    },

    focusWindow: (id) => {
        const { windows, focusedWindowId, nextZIndex } = get();
        if (focusedWindowId === id) return;

        const newWindows = new Map(windows);
        newWindows.forEach((w) => {
            w.isFocused = w.id === id;
        });

        const targetWindow = newWindows.get(id);
        if (targetWindow) {
            targetWindow.zIndex = nextZIndex;
            targetWindow.isMinimized = false; // Restore if minimized
        }

        set({
            windows: newWindows,
            focusedWindowId: id,
            nextZIndex: nextZIndex + 1,
        });
    },

    minimizeWindow: (id) => {
        const { windows, focusedWindowId } = get();
        const newWindows = new Map(windows);
        const targetWindow = newWindows.get(id);

        if (targetWindow) {
            targetWindow.isMinimized = true;
            targetWindow.isFocused = false;
        }

        // Focus next window
        let newFocusedId: string | null = null;
        if (focusedWindowId === id) {
            let maxZ = -1;
            newWindows.forEach((w) => {
                if (w.zIndex > maxZ && !w.isMinimized && w.id !== id) {
                    maxZ = w.zIndex;
                    newFocusedId = w.id;
                }
            });
            if (newFocusedId) {
                const focusedWindow = newWindows.get(newFocusedId);
                if (focusedWindow) {
                    focusedWindow.isFocused = true;
                }
            }
        }

        set({
            windows: newWindows,
            focusedWindowId: focusedWindowId === id ? newFocusedId : focusedWindowId,
        });
    },

    maximizeWindow: (id) => {
        const { windows } = get();
        const newWindows = new Map(windows);
        const targetWindow = newWindows.get(id);

        if (targetWindow) {
            if (!targetWindow.isMaximized) {
                // Store current position/size for restore
                (targetWindow as WindowState & { _restore?: { position: typeof targetWindow.position; size: typeof targetWindow.size } })._restore = {
                    position: { ...targetWindow.position },
                    size: { ...targetWindow.size },
                };
                targetWindow.isMaximized = true;
                targetWindow.position = { x: 0, y: 0 };
                targetWindow.size = {
                    width: window.innerWidth,
                    height: window.innerHeight - 48, // Account for taskbar
                };
            } else {
                // Restore
                const restore = (targetWindow as WindowState & { _restore?: { position: typeof targetWindow.position; size: typeof targetWindow.size } })._restore;
                if (restore) {
                    targetWindow.position = restore.position;
                    targetWindow.size = restore.size;
                }
                targetWindow.isMaximized = false;
            }
        }

        set({ windows: newWindows });
    },

    restoreWindow: (id) => {
        const { windows, nextZIndex } = get();
        const newWindows = new Map(windows);
        newWindows.forEach((w) => {
            w.isFocused = w.id === id;
        });

        const targetWindow = newWindows.get(id);
        if (targetWindow) {
            targetWindow.isMinimized = false;
            targetWindow.zIndex = nextZIndex;
        }

        set({
            windows: newWindows,
            focusedWindowId: id,
            nextZIndex: nextZIndex + 1,
        });
    },

    moveWindow: (id, x, y) => {
        const { windows } = get();
        const newWindows = new Map(windows);
        const targetWindow = newWindows.get(id);

        if (targetWindow && !targetWindow.isMaximized) {
            targetWindow.position = { x, y };
            set({ windows: newWindows });
        }
    },

    resizeWindow: (id, width, height) => {
        const { windows } = get();
        const newWindows = new Map(windows);
        const targetWindow = newWindows.get(id);

        if (targetWindow && !targetWindow.isMaximized) {
            targetWindow.size = {
                width: Math.max(300, width),
                height: Math.max(200, height),
            };
            set({ windows: newWindows });
        }
    },

    getWindow: (id) => {
        return get().windows.get(id);
    },
}));
