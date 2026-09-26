import { defineConfig, devices } from "@playwright/test";

// Browser tests run against the generated site, served statically.
export default defineConfig({
  testDir: "tests",
  reporter: "list",
  use: { ...devices["Desktop Chrome"], baseURL: "http://localhost:4173" },
  webServer: {
    command: "npx serve .output/public -l 4173",
    url: "http://localhost:4173/",
    reuseExistingServer: !process.env.CI,
  },
});
