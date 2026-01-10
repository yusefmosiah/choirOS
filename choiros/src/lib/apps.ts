// App Registry
import type { ComponentType } from 'react';
import { FileText, Folder, Terminal, Mail } from 'lucide-react';

export interface AppDefinition {
    id: string;
    title: string;
    icon: ComponentType<{ size?: number }>;
    defaultSize: { width: number; height: number };
    fileTypes?: string[];
}

export const APP_REGISTRY: Record<string, AppDefinition> = {
    writer: {
        id: 'writer',
        title: 'Writer',
        icon: FileText,
        defaultSize: { width: 800, height: 600 },
        fileTypes: ['.md', '.txt', '.json'],
    },
    files: {
        id: 'files',
        title: 'Files',
        icon: Folder,
        defaultSize: { width: 700, height: 500 },
    },
    terminal: {
        id: 'terminal',
        title: 'Terminal',
        icon: Terminal,
        defaultSize: { width: 700, height: 450 },
    },
    mail: {
        id: 'mail',
        title: 'Mail',
        icon: Mail,
        defaultSize: { width: 1000, height: 600 },
    },
};

export function getAppForFileType(mimeType: string): string {
    // Default to writer for text-based files
    if (mimeType.startsWith('text/') || mimeType === 'application/json') {
        return 'writer';
    }
    return 'files';
}
