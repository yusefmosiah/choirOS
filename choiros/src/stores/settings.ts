// Settings Store - user preferences and provider configuration
import { create } from 'zustand';

type ProviderType = 'bedrock' | 'zai';
type ProviderStatus = 'active' | 'testing' | 'error';

interface ProviderConfig {
    provider: ProviderType;
    model: string;
    status: ProviderStatus;
}

interface TestResult {
    provider: string;
    valid: boolean;
    latency_ms?: number;
    model: string;
    error?: string;
}

interface SettingsState {
    // Current provider configuration
    providerConfig: ProviderConfig;

    // Actions
    setProvider: (provider: ProviderType) => Promise<void>;
    testProvider: (provider: ProviderType) => Promise<TestResult>;
    refreshProvider: () => Promise<void>;
}

const PROVIDER_INFO = {
    bedrock: {
        name: 'AWS Bedrock',
        model: 'us.anthropic.claude-opus-4-5-20251101-v1:0',
        description: 'Claude Opus 4.5 on AWS Bedrock',
    },
    zai: {
        name: 'Z.ai',
        model: 'glm-4.7',
        description: 'GLM-4.7 on Z.ai',
    },
} as const;

export const useSettingsStore = create<SettingsState>((set, get) => ({
    providerConfig: {
        provider: 'bedrock',
        model: 'us.anthropic.claude-opus-4-5-20251101-v1:0',
        status: 'active',
    },

    setProvider: async (provider: ProviderType) => {
        set((state) => ({
            providerConfig: { ...state.providerConfig, status: 'testing' },
        }));

        try {
            const response = await fetch('/api/settings/provider', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider }),
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to set provider');
            }

            const data = await response.json();

            set({
                providerConfig: {
                    provider: data.provider,
                    model: data.model,
                    status: 'active',
                },
            });
        } catch (error) {
            set((state) => ({
                providerConfig: { ...state.providerConfig, status: 'error' },
            }));
            throw error;
        }
    },

    testProvider: async (provider: ProviderType) => {
        try {
            const response = await fetch('/api/settings/provider/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider }),
            });

            if (!response.ok) {
                throw new Error('Failed to test provider');
            }

            return await response.json();
        } catch (error) {
            return {
                provider,
                valid: false,
                model: PROVIDER_INFO[provider].model,
                error: error instanceof Error ? error.message : 'Unknown error',
            };
        }
    },

    refreshProvider: async () => {
        try {
            const response = await fetch('/api/settings/provider');
            if (!response.ok) return;

            const data = await response.json();
            set({
                providerConfig: {
                    provider: data.provider,
                    model: data.model,
                    status: data.status || 'active',
                },
            });
        } catch (error) {
            console.error('Failed to refresh provider config:', error);
        }
    },
}));

// Helper hook to get provider display info
export function useProviderInfo(provider: ProviderType) {
    return PROVIDER_INFO[provider];
}

// Initialize provider config on store creation
useSettingsStore.getState().refreshProvider();
