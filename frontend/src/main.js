import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'

import App from './App.vue'
import router from './router'
import i18n from './i18n'
import { useAuthStore } from './stores/auth'
import { useProjectStore } from './stores/project'

import '@/styles/global.scss'
import '@/styles/auth.scss'
import '@/styles/element-plus-theme.scss'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(i18n)
app.use(ElementPlus)

// 把 i18n 挂到 window，方便浏览器控制台调试
window.__i18n = i18n

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

async function bootstrap() {
  const auth = useAuthStore()
  const projectStore = useProjectStore()
  const restored = await auth.restoreSession()
  if (restored) {
    await projectStore.fetchProjects()
  }
  app.mount('#app')
}

bootstrap()
