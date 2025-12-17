// Desktop Icon Component
import { useRef, type ComponentType } from 'react';
import './Icon.css';

interface IconProps {
    icon: ComponentType<{ size?: number }>;
    label: string;
    onDoubleClick: () => void;
}

export function Icon({ icon: IconComponent, label, onDoubleClick }: IconProps) {
    const lastTapRef = useRef<number>(0);
    const DOUBLE_TAP_DELAY = 300; // ms

    const handleTouchEnd = () => {
        const now = Date.now();
        if (now - lastTapRef.current < DOUBLE_TAP_DELAY) {
            // Double tap detected
            onDoubleClick();
            lastTapRef.current = 0;
        } else {
            lastTapRef.current = now;
        }
    };

    return (
        <button
            className="desktop-icon"
            onDoubleClick={onDoubleClick}
            onTouchEnd={handleTouchEnd}
            type="button"
        >
            <div className="desktop-icon-image">
                <IconComponent size={40} />
            </div>
            <span className="desktop-icon-label">{label}</span>
        </button>
    );
}
