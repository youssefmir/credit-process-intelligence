import { defineConfig } from "@playwright/test";

const port = 4173;
const base = process.env.BASE_PATH ?? "/credit-process-intelligence/";

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: `http://127.0.0.1:${port}${base}`,
    trace: "off",
  },
  webServer: {
    command: `npx vite preview --port ${port} --strictPort --host 127.0.0.1`,
    url: `http://127.0.0.1:${port}${base}`,
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
