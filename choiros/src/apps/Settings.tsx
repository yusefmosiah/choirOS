// Settings App - user preferences and provider selection
import { useEffect } from 'react';
import { useSettingsStore, useProviderInfo } from '@/stores/settings';

export function SettingsApp() {
    const { providerConfig, setProvider, testProvider, refreshProvider } = useSettingsStore();
    const providerInfo = useProviderInfo(providerConfig.provider);

    useEffect(() => {
        refreshProvider();
    }, [refreshProvider]);

    const handleProviderChange = async (newProvider: 'bedrock' | 'zai') => {
        try {
            await setProvider(newProvider);
        } catch (error) {
            console.error('Failed to switch provider:', error);
        }
    };

    const handleTestProvider = async () => {
        const result = await testProvider(providerConfig.provider);
        if (result.valid) {
            alert(`✅ Provider test passed!\nLatency: ${result.latency_ms}ms\nModel: ${result.model}`);
        } else {
            alert(`❌ Provider test failed!\nError: ${result.error || 'Unknown error'}`);
        }
    };

    return (
        <div className="settings-app" style={{ padding: '24px', height: '100%', overflow: 'auto' }}>
            <h2 style={{ marginBottom: '24px', fontSize: '24px', fontWeight: '600' }}>
                Settings
            </h2>

            <section style={{ marginBottom: '32px' }}>
                <h3 style={{ marginBottom: '16px', fontSize: '18px', fontWeight: '500' }}>
                    AI Provider
                </h3>

                <div style={{ marginBottom: '16px' }}>
                    <label
                        htmlFor="provider-select"
                        style={{ display: 'block', marginBottom: '8px', fontSize: '14px', fontWeight: '500' }}
                    >
                        Current Provider
                    </label>
                    <select
                        id="provider-select"
                        value={providerConfig.provider}
                        onChange={(e) => handleProviderChange(e.target.value as 'bedrock' | 'zai')}
                        disabled={providerConfig.status === 'testing'}
                        style={{
                            width: '100%',
                            padding: '10px 12px',
                            fontSize: '14px',
                            border: '1px solid #e5e7eb',
                            borderRadius: '6px',
                            backgroundColor: '#fff',
                            cursor: providerConfig.status === 'testing' ? 'not-allowed' : 'pointer',
                            opacity: providerConfig.status === 'testing' ? 0.6 : 1,
                        }}
                    >
                        <option value="bedrock">AWS Bedrock (Claude Opus 4.5)</option>
                        <option value="zai">Z.ai (GLM-4.7)</option>
                    </select>
                </div>

                <div style={{ marginBottom: '16px' }}>
                    <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>
                        <strong>Model:</strong> {providerConfig.model}
                    </div>
                    <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>
                        <strong>Status:</strong>{' '}
                        <span
                            style={{
                                color:
                                    providerConfig.status === 'active'
                                        ? '#059669'
                                        : providerConfig.status === 'testing'
                                        ? '#d97706'
                                        : '#dc2626',
                            }}
                        >
                            {providerConfig.status.toUpperCase()}
                        </span>
                    </div>
                    <div style={{ fontSize: '13px', color: '#6b7280' }}>
                        <strong>Description:</strong> {providerInfo.description}
                    </div>
                </div>

                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                    <button
                        onClick={handleTestProvider}
                        disabled={providerConfig.status === 'testing'}
                        style={{
                            padding: '8px 16px',
                            fontSize: '13px',
                            fontWeight: '500',
                            color: '#fff',
                            backgroundColor: providerConfig.status === 'testing' ? '#9ca3af' : '#3b82f6',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: providerConfig.status === 'testing' ? 'not-allowed' : 'pointer',
                        }}
                    >
                        Test Connection
                    </button>
                    {providerConfig.status === 'testing' && (
                        <span style={{ fontSize: '13px', color: '#6b7280' }}>Switching providers...</span>
                    )}
                </div>
            </section>

            <section style={{ borderTop: '1px solid #e5e7eb', paddingTop: '24px' }}>
                <h3 style={{ marginBottom: '16px', fontSize: '18px', fontWeight: '500' }}>
                    About
                </h3>
                <div style={{ fontSize: '13px', color: '#6b7280', lineHeight: '1.6' }}>
                    <p style={{ marginBottom: '8px' }}>
                        <strong>ChoirOS Settings</strong>
                    </p>
                    <p style={{ marginBottom: '8px' }}>
                        Configure your AI provider and model preferences here. Changes take effect
                        immediately for all new conversations.
                    </p>
                    <p>
                        <strong>Providers:</strong>
                    </p>
                    <ul style={{ marginLeft: '20px', marginBottom: '8px' }}>
                        <li>
                            <strong>AWS Bedrock:</strong> Official Claude Opus 4.5 hosted on AWS
                        </li>
                        <li>
                            <strong>Z.ai:</strong> GLM-4.7 with Anthropic-compatible API
                        </li>
                    </ul>
                </div>
            </section>
        </div>
    );
}
