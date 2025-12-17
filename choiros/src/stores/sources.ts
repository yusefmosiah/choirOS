/**
 * Artifact store for managing parsed sources
 */

import { create } from 'zustand';
import {
    listArtifacts,
    getArtifact,
    parseUrl,
    parseUpload,
    checkUrl,
    deleteArtifact as apiDeleteArtifact,
    type ArtifactListItem,
    type Artifact,
    type ParseUrlResponse,
    type CheckUrlResponse,
    type ParseMode,
} from '../lib/api';

interface SourcesState {
    // List of artifacts (without full content)
    artifacts: ArtifactListItem[];

    // Full artifacts by ID (cached)
    artifactCache: Map<string, Artifact>;

    // Loading states
    isLoading: boolean;
    isParsingUrl: boolean;
    isUploading: boolean;

    // Error state
    error: string | null;

    // Actions
    fetchArtifacts: () => Promise<void>;
    loadArtifact: (id: string) => Promise<Artifact | null>;
    checkUrlExists: (url: string) => Promise<CheckUrlResponse>;
    parseUrlAndCreate: (url: string, mode?: ParseMode) => Promise<ParseUrlResponse | null>;
    uploadAndParse: (file: File) => Promise<ParseUrlResponse | null>;
    deleteArtifact: (id: string) => Promise<boolean>;
    clearError: () => void;
}

export const useSourcesStore = create<SourcesState>((set, get) => ({
    artifacts: [],
    artifactCache: new Map(),
    isLoading: false,
    isParsingUrl: false,
    isUploading: false,
    error: null,

    fetchArtifacts: async () => {
        set({ isLoading: true, error: null });
        try {
            const response = await listArtifacts();
            set({ artifacts: response.artifacts, isLoading: false });
        } catch (e) {
            set({
                error: e instanceof Error ? e.message : 'Failed to fetch artifacts',
                isLoading: false
            });
        }
    },

    loadArtifact: async (id: string) => {
        // Check cache first
        const cached = get().artifactCache.get(id);
        if (cached) return cached;

        try {
            const artifact = await getArtifact(id);
            set(state => ({
                artifactCache: new Map(state.artifactCache).set(id, artifact),
            }));
            return artifact;
        } catch (e) {
            set({ error: e instanceof Error ? e.message : 'Failed to load artifact' });
            return null;
        }
    },

    checkUrlExists: async (url: string) => {
        return await checkUrl(url);
    },

    parseUrlAndCreate: async (url: string, mode: ParseMode = 'create') => {
        set({ isParsingUrl: true, error: null });
        try {
            const result = await parseUrl(url, mode);
            // Refresh the list to include new artifact
            await get().fetchArtifacts();
            set({ isParsingUrl: false });
            return result;
        } catch (e) {
            set({
                error: e instanceof Error ? e.message : 'Failed to parse URL',
                isParsingUrl: false
            });
            return null;
        }
    },

    uploadAndParse: async (file: File) => {
        set({ isUploading: true, error: null });
        try {
            const result = await parseUpload(file);
            // Refresh the list to include new artifact
            await get().fetchArtifacts();
            set({ isUploading: false });
            return result;
        } catch (e) {
            set({
                error: e instanceof Error ? e.message : 'Failed to parse file',
                isUploading: false
            });
            return null;
        }
    },

    deleteArtifact: async (id: string) => {
        try {
            await apiDeleteArtifact(id);
            // Remove from local state
            set(state => ({
                artifacts: state.artifacts.filter(a => a.id !== id),
                artifactCache: (() => {
                    const cache = new Map(state.artifactCache);
                    cache.delete(id);
                    return cache;
                })(),
            }));
            return true;
        } catch (e) {
            set({ error: e instanceof Error ? e.message : 'Failed to delete artifact' });
            return false;
        }
    },

    clearError: () => set({ error: null }),
}));
