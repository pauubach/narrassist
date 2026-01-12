import { defineConfig, devices } from '@playwright/test'

/**
 * Configuración de Playwright para tests E2E
 * Ver: https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',

  // Tiempo máximo por test (aumentado para estabilidad)
  timeout: 60 * 1000,

  // Expect timeout (aumentado para elementos que tardan en cargar)
  expect: {
    timeout: 10000
  },

  // Ejecutar tests en paralelo
  fullyParallel: true,

  // Fallar el build si quedan tests con .only
  forbidOnly: !!process.env.CI,

  // Reintentos (1 localmente, 2 en CI para mayor estabilidad)
  retries: process.env.CI ? 2 : 1,

  // Workers (menos en CI para evitar race conditions)
  workers: process.env.CI ? 1 : 4,

  // Reporter
  reporter: [
    ['html'],
    ['list'],
    ['json', { outputFile: 'test-results/results.json' }]
  ],

  // Configuración compartida para todos los tests
  use: {
    // Base URL del servidor de desarrollo
    baseURL: 'http://localhost:5173',

    // Capturar screenshots solo en fallos
    screenshot: 'only-on-failure',

    // Capturar videos solo en fallos
    video: 'retain-on-failure',

    // Traces on retry
    trace: 'on-first-retry',

    // Action timeout (para clicks, fills, etc.)
    actionTimeout: 15000,

    // Navigation timeout
    navigationTimeout: 30000,
  },

  // Configurar proyectos para diferentes navegadores
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    // Tests en mobile viewports
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

  // Servidor de desarrollo
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
})
