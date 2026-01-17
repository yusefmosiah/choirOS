import { defineConfig } from '@playwright/test';

const port = Number(process.env.E2E_PORT || 5173);
const host = process.env.E2E_HOST || '127.0.0.1';
const baseURL = `http://${host}:${port}`;

export default defineConfig({
    testDir: './tests/e2e',
    timeout: 30_000,
    expect: {
        timeout: 5_000,
    },
    use: {
        baseURL,
        headless: true,
    },
    webServer: {
        command: `npm run dev -- --host ${host} --port ${port}`,
        url: baseURL,
        reuseExistingServer: !process.env.CI,
        env: {
            VITE_NATS_WS_URL: process.env.VITE_NATS_WS_URL || 'ws://localhost:8080',
            VITE_USER_ID: process.env.VITE_USER_ID || 'local',
        },
    },
});
