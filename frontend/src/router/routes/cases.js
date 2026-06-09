import FunctionalCaseWorkspaceView from '@/views/cases/FunctionalCaseWorkspaceView.vue'
import ApiTestWorkspaceView from '@/views/cases/ApiTestWorkspaceView.vue'
import ApiCaseDetailView from '@/views/cases/ApiCaseDetailView.vue'

export default [
  {
    path: '/cases/functional',
    name: 'FunctionalCases',
    component: FunctionalCaseWorkspaceView,
    meta: { titleKey: 'menu.casesFunctional', projectRequired: true },
  },
  {
    path: '/cases/api',
    name: 'ApiCases',
    component: ApiTestWorkspaceView,
    meta: { titleKey: 'menu.casesApi', projectRequired: true },
  },
  {
    path: '/cases/api/cases/:caseId',
    name: 'ApiCaseDetail',
    component: ApiCaseDetailView,
    meta: { titleKey: 'menu.casesApi', projectRequired: true },
  },
]
