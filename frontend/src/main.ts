// Interceptor de console → archivo (DEBE ser lo primero)
import { installConsoleInterceptor } from '@/services/logger'
installConsoleInterceptor()

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import ConfirmationService from 'primevue/confirmationservice'
import Tooltip from 'primevue/tooltip'
import App from './App.vue'
import router from './router'

// PrimeVue 4 - Tema Aura como base inicial
import Aura from '@primevue/themes/aura'

// PrimeIcons
import 'primeicons/primeicons.css'

// Fuentes (locales para funcionamiento offline)
import './assets/fonts/fonts-local.css'

// Estilos globales
import './assets/main.css'
import './assets/themes.css'
import './assets/animations.css'

// Design System tokens, utilities y accesibilidad
import './assets/design-system/tokens.css'
import './assets/design-system/utilities.css'
import './assets/design-system/accessibility.css'

// Overrides de PrimeVue - DEBE cargarse después del tema
import './assets/primevue-overrides.css'

const pinia = createPinia()
const app = createApp(App)

// Plugins
app.use(pinia)
app.use(router)
app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      prefix: 'p',
      darkModeSelector: '.dark',
      cssLayer: false
    }
  },
  ripple: true
})
app.use(ToastService)
app.use(ConfirmationService)

// Directivas
app.directive('tooltip', Tooltip)

// Inicializar el store de tema después de montar para aplicar configuración guardada
import { useThemeStore } from './stores/theme'

app.mount('#app')

// Inicializar tema después de montar la app
const themeStore = useThemeStore()
themeStore.initialize()
