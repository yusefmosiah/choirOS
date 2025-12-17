// Window Component
import { useRef, useState, useCallback, type MouseEvent } from 'react';
import { Minus, Square, X, Maximize2 } from 'lucide-react';
import { useWindowStore, type WindowState } from '../../stores/windows';
import './Window.css';

interface WindowProps {
    windowState: WindowState;
    children: React.ReactNode;
}

type ResizeDirection = 'n' | 's' | 'e' | 'w' | 'ne' | 'nw' | 'se' | 'sw' | null;

export function Window({ windowState, children }: WindowProps) {
    const { id, title, position, size, zIndex, isMaximized, isFocused } = windowState;

    const closeWindow = useWindowStore((s) => s.closeWindow);
    const focusWindow = useWindowStore((s) => s.focusWindow);
    const minimizeWindow = useWindowStore((s) => s.minimizeWindow);
    const maximizeWindow = useWindowStore((s) => s.maximizeWindow);
    const moveWindow = useWindowStore((s) => s.moveWindow);
    const resizeWindow = useWindowStore((s) => s.resizeWindow);

    const [isDragging, setIsDragging] = useState(false);
    const [isResizing, setIsResizing] = useState(false);
    const dragStart = useRef({ x: 0, y: 0, winX: 0, winY: 0 });
    const resizeStart = useRef({ x: 0, y: 0, width: 0, height: 0, winX: 0, winY: 0 });

    // Drag handling (mouse)
    const handleTitleBarMouseDown = useCallback((e: MouseEvent) => {
        if (isMaximized) return;
        e.preventDefault();
        setIsDragging(true);
        dragStart.current = {
            x: e.clientX,
            y: e.clientY,
            winX: position.x,
            winY: position.y,
        };

        const handleMouseMove = (e: globalThis.MouseEvent) => {
            const dx = e.clientX - dragStart.current.x;
            const dy = e.clientY - dragStart.current.y;
            moveWindow(id, dragStart.current.winX + dx, dragStart.current.winY + dy);
        };

        const handleMouseUp = () => {
            setIsDragging(false);
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
    }, [id, isMaximized, moveWindow, position]);

    // Touch drag handling (mobile)
    const handleTitleBarTouchStart = useCallback((e: React.TouchEvent) => {
        if (isMaximized) return;
        const touch = e.touches[0];
        setIsDragging(true);
        dragStart.current = {
            x: touch.clientX,
            y: touch.clientY,
            winX: position.x,
            winY: position.y,
        };
    }, [isMaximized, position]);

    const handleTitleBarTouchMove = useCallback((e: React.TouchEvent) => {
        if (!isDragging || isMaximized) return;
        e.preventDefault();
        const touch = e.touches[0];
        const dx = touch.clientX - dragStart.current.x;
        const dy = touch.clientY - dragStart.current.y;
        moveWindow(id, dragStart.current.winX + dx, dragStart.current.winY + dy);
    }, [id, isDragging, isMaximized, moveWindow]);

    const handleTitleBarTouchEnd = useCallback(() => {
        setIsDragging(false);
    }, []);

    // Resize handling
    const handleResizeMouseDown = useCallback((e: MouseEvent, direction: ResizeDirection) => {
        if (isMaximized) return;
        e.preventDefault();
        e.stopPropagation();
        setIsResizing(true);
        resizeStart.current = {
            x: e.clientX,
            y: e.clientY,
            width: size.width,
            height: size.height,
            winX: position.x,
            winY: position.y,
        };

        const handleMouseMove = (e: globalThis.MouseEvent) => {
            const dx = e.clientX - resizeStart.current.x;
            const dy = e.clientY - resizeStart.current.y;

            let newWidth = resizeStart.current.width;
            let newHeight = resizeStart.current.height;
            let newX = resizeStart.current.winX;
            let newY = resizeStart.current.winY;

            if (direction?.includes('e')) newWidth += dx;
            if (direction?.includes('w')) {
                newWidth -= dx;
                newX += dx;
            }
            if (direction?.includes('s')) newHeight += dy;
            if (direction?.includes('n')) {
                newHeight -= dy;
                newY += dy;
            }

            // Minimum size
            if (newWidth >= 300 && newHeight >= 200) {
                resizeWindow(id, newWidth, newHeight);
                if (direction?.includes('w') || direction?.includes('n')) {
                    moveWindow(id, newX, newY);
                }
            }
        };

        const handleMouseUp = () => {
            setIsResizing(false);
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
    }, [id, isMaximized, moveWindow, resizeWindow, position, size]);

    // Touch resize handling (for the resize grip)
    const resizeDirectionRef = useRef<ResizeDirection>(null);

    const handleResizeTouchStart = useCallback((e: React.TouchEvent, direction: ResizeDirection) => {
        if (isMaximized) return;
        e.preventDefault();
        const touch = e.touches[0];
        setIsResizing(true);
        resizeDirectionRef.current = direction;
        resizeStart.current = {
            x: touch.clientX,
            y: touch.clientY,
            width: size.width,
            height: size.height,
            winX: position.x,
            winY: position.y,
        };
    }, [isMaximized, position, size]);

    const handleResizeTouchMove = useCallback((e: React.TouchEvent) => {
        if (!isResizing || isMaximized) return;
        e.preventDefault();
        const touch = e.touches[0];
        const direction = resizeDirectionRef.current;

        const dx = touch.clientX - resizeStart.current.x;
        const dy = touch.clientY - resizeStart.current.y;

        let newWidth = resizeStart.current.width;
        let newHeight = resizeStart.current.height;
        let newX = resizeStart.current.winX;
        let newY = resizeStart.current.winY;

        if (direction?.includes('e')) newWidth += dx;
        if (direction?.includes('w')) {
            newWidth -= dx;
            newX += dx;
        }
        if (direction?.includes('s')) newHeight += dy;
        if (direction?.includes('n')) {
            newHeight -= dy;
            newY += dy;
        }

        // Minimum size
        if (newWidth >= 280 && newHeight >= 200) {
            resizeWindow(id, newWidth, newHeight);
            if (direction?.includes('w') || direction?.includes('n')) {
                moveWindow(id, newX, newY);
            }
        }
    }, [id, isResizing, isMaximized, moveWindow, resizeWindow]);

    const handleResizeTouchEnd = useCallback(() => {
        setIsResizing(false);
        resizeDirectionRef.current = null;
    }, []);

    const handleWindowClick = () => {
        if (!isFocused) {
            focusWindow(id);
        }
    };

    return (
        <div
            className={`window ${isFocused ? 'focused' : ''} ${isDragging ? 'dragging' : ''} ${isResizing ? 'resizing' : ''}`}
            style={{
                transform: isMaximized ? 'none' : `translate(${position.x}px, ${position.y}px)`,
                width: isMaximized ? '100%' : size.width,
                height: isMaximized ? `calc(100% - var(--taskbar-height))` : size.height,
                zIndex,
                top: isMaximized ? 0 : undefined,
                left: isMaximized ? 0 : undefined,
            }}
            onMouseDown={handleWindowClick}
        >
            {/* Title bar */}
            <div
                className="window-titlebar"
                onMouseDown={handleTitleBarMouseDown}
                onTouchStart={handleTitleBarTouchStart}
                onTouchMove={handleTitleBarTouchMove}
                onTouchEnd={handleTitleBarTouchEnd}
                onDoubleClick={() => maximizeWindow(id)}
            >
                <span className="window-title">{title}</span>
                <div className="window-controls">
                    <button
                        className="window-control minimize"
                        onClick={(e) => { e.stopPropagation(); minimizeWindow(id); }}
                        title="Minimize"
                    >
                        <Minus size={14} />
                    </button>
                    <button
                        className="window-control maximize"
                        onClick={(e) => { e.stopPropagation(); maximizeWindow(id); }}
                        title={isMaximized ? 'Restore' : 'Maximize'}
                    >
                        {isMaximized ? <Square size={12} /> : <Maximize2 size={14} />}
                    </button>
                    <button
                        className="window-control close"
                        onClick={(e) => { e.stopPropagation(); closeWindow(id); }}
                        title="Close"
                    >
                        <X size={14} />
                    </button>
                </div>
            </div>

            {/* Content */}
            <div className="window-content">
                {children}
            </div>

            {/* Resize handles */}
            {!isMaximized && (
                <>
                    <div className="window-resize-handle n" onMouseDown={(e) => handleResizeMouseDown(e, 'n')} />
                    <div className="window-resize-handle s" onMouseDown={(e) => handleResizeMouseDown(e, 's')} />
                    <div className="window-resize-handle e" onMouseDown={(e) => handleResizeMouseDown(e, 'e')} />
                    <div className="window-resize-handle w" onMouseDown={(e) => handleResizeMouseDown(e, 'w')} />
                    <div className="window-resize-handle ne" onMouseDown={(e) => handleResizeMouseDown(e, 'ne')} />
                    <div className="window-resize-handle nw" onMouseDown={(e) => handleResizeMouseDown(e, 'nw')} />
                    <div
                        className="window-resize-handle se resize-grip"
                        onMouseDown={(e) => handleResizeMouseDown(e, 'se')}
                        onTouchStart={(e) => handleResizeTouchStart(e, 'se')}
                        onTouchMove={handleResizeTouchMove}
                        onTouchEnd={handleResizeTouchEnd}
                    />
                    <div className="window-resize-handle sw" onMouseDown={(e) => handleResizeMouseDown(e, 'sw')} />
                </>
            )}
        </div>
    );
}
