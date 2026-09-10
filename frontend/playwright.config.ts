import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  timeout: 90000,
  workers: 1,
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:3000",
    headless: true,
    channel: "chrome",
    screenshot: "only-on-failure",
    launchOptions: {
      args: process.env.E2E_CAMERA_FILE
        ? [
            "--use-fake-device-for-media-stream",
            "--use-fake-ui-for-media-stream",
            "--use-file-for-fake-video-capture=" + process.env.E2E_CAMERA_FILE,
          ]
        : [],
    },
  },
  reporter: "list",
});
