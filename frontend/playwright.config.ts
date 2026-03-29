import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5199',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: [
    {
      command: 'python -X utf8 -c "from api.cli import main; main()" serve --port 9099 --database-url sqlite:///:memory:',
      cwd: '..',
      url: 'http://localhost:9099/api/notes',
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
      env: { PYTHONUTF8: '1' },
    },
    {
      command: 'npx vite --port 5199',
      url: 'http://localhost:5199',
      reuseExistingServer: !process.env.CI,
      timeout: 15_000,
      env: { VITE_API_URL: 'http://localhost:9099' },
    },
  ],
});
