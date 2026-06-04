import AgentCenterView from '@/views/agent/AgentCenterView.vue'

export default [
  {
    path: '/agent',
    name: 'AgentCenter',
    component: AgentCenterView,
    meta: { titleKey: 'menu.agent', projectRequired: true, flushBottom: true },
  },
]
