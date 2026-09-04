import { defineConfig } from "@playwright/test";

export default defineConfig({
    testDir: "./e2e",
    fullyParallel: false,
    workers: 1,
    timeout: 45_000,
    use: {
        browserName: "chromium",
        headless: true,
        viewport: { width: 1100, height: 900 },
    },
});
