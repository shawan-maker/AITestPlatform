import LoginView from '@/views/auth/LoginView.vue'
import RegisterView from '@/views/auth/RegisterView.vue'

export default [
  {
    path: 'login',
    name: 'Login',
    component: LoginView,
    meta: { requiresAuth: false },
  },
  {
    path: 'register',
    name: 'Register',
    component: RegisterView,
    meta: { requiresAuth: false },
  },
]
