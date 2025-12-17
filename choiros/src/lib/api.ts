/**
 * API client for ChoirOS backend
 */

const API_BASE = 'http://localhost:8000/api';

export interface ParseUrlResponse {
    artifact_id: string;
    path: string;
    name: string;
    mime_type: string;
    source_type: 'youtube' | 'web' | 'upload';
    content_preview: string;
}

export interface CheckUrlResponse {
    exists: boolean;
    artifact_id?: string;
    name?: string;
}

export interface DuplicateError {
    error: 'duplicate';
    artifact_id: string;
    name: string;
}

export interface Artifact {
    id: string;
    path: string;
    name: string;
    mime_type: string;
    content: string;
    source_url: string | null;
    source_type: string;
    created_at: string;
    metadata: Record<string, unknown>;
}

export interface ArtifactListItem {
    id: string;
    path: string;
    name: string;
    mime_type: string;
    source_url: string | null;
    source_type: string;
    created_at: string;
    content_preview: string;
}

export interface ArtifactListResponse {
    artifacts: ArtifactListItem[];
    total: number;
}

export type ParseMode = 'create' | 'overwrite' | 'keep_both';

/**
 * Check if a URL has already been parsed
 */
export async function checkUrl(url: string): Promise<CheckUrlResponse> {
    const response = await fetch(`${API_BASE}/parse/check-url`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
    });

    if (!response.ok) {
        throw new Error('Failed to check URL');
    }

    return response.json();
}

/**
 * Parse a URL (YouTube or web page) and create an artifact
 */
export async function parseUrl(url: string, mode: ParseMode = 'create'): Promise<ParseUrlResponse> {
    const response = await fetch(`${API_BASE}/parse/url`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url, mode }),
    });

    if (!response.ok) {
        const error = await response.json();
        // Check for duplicate error
        if (response.status === 409 && error.detail?.error === 'duplicate') {
            const dupError = new Error('Duplicate URL') as Error & { duplicate: DuplicateError };
            dupError.duplicate = error.detail;
            throw dupError;
        }
        throw new Error(error.detail || 'Failed to parse URL');
    }

    return response.json();
}

/**
 * Upload and parse a file
 */
export async function parseUpload(file: File): Promise<ParseUrlResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/parse/upload`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to parse file');
    }

    return response.json();
}

/**
 * Get all artifacts
 */
export async function listArtifacts(): Promise<ArtifactListResponse> {
    const response = await fetch(`${API_BASE}/artifacts`);

    if (!response.ok) {
        throw new Error('Failed to fetch artifacts');
    }

    return response.json();
}

/**
 * Get a single artifact by ID (with full content)
 */
export async function getArtifact(id: string): Promise<Artifact> {
    const response = await fetch(`${API_BASE}/artifacts/${id}`);

    if (!response.ok) {
        throw new Error('Failed to fetch artifact');
    }

    return response.json();
}

/**
 * Delete an artifact
 */
export async function deleteArtifact(id: string): Promise<void> {
    const response = await fetch(`${API_BASE}/artifacts/${id}`, {
        method: 'DELETE',
    });

    if (!response.ok) {
        throw new Error('Failed to delete artifact');
    }
}

/**
 * Check if a string looks like a URL
 */
export function isUrl(str: string): boolean {
    try {
        const url = new URL(str.trim());
        return url.protocol === 'http:' || url.protocol === 'https:';
    } catch {
        return false;
    }
}
