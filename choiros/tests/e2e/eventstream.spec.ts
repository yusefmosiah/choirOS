import { test, expect } from '@playwright/test';
import { connect } from 'nats';
import { randomUUID } from 'crypto';

const NATS_URL = process.env.NATS_URL || 'nats://localhost:4222';
const USER_ID = process.env.VITE_USER_ID || 'local';
const NATS_USER = process.env.NATS_USER;
const NATS_PASSWORD = process.env.NATS_PASSWORD;

function buildEvent(path: string) {
    return {
        id: randomUUID(),
        timestamp: Date.now(),
        user_id: USER_ID,
        source: 'agent',
        event_type: 'file.write',
        payload: {
            path,
            content_hash: 'test',
            size_bytes: 4,
        },
    };
}

test('EventStream renders file.write events from NATS', async ({ page }) => {
    await page.goto('/');
    await page.waitForSelector('.desktop', { state: 'visible' });

    const options: { servers: string; user?: string; pass?: string } = { servers: NATS_URL };
    if (NATS_USER && NATS_PASSWORD) {
        options.user = NATS_USER;
        options.pass = NATS_PASSWORD;
    }
    const nc = await connect(options);

    const event = buildEvent('tmp/test.txt');
    const subject = `choiros.${USER_ID}.${event.source}.${event.event_type}`;

    nc.publish(subject, JSON.stringify(event));
    await nc.flush();

    await expect(page.locator('.event-item .event-message', { hasText: 'file.write tmp/test.txt' }))
        .toBeVisible();

    await nc.drain();
});
