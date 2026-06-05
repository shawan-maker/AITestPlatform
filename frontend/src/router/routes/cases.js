import RequirementListView from '@/views/cases/RequirementListView.vue'
import RequirementDetailView from '@/views/cases/RequirementDetailView.vue'
import RequirementViewOnlyView from '@/views/cases/RequirementViewOnlyView.vue'
import FunctionalCaseWorkspaceView from '@/views/cases/FunctionalCaseWorkspaceView.vue'
import ApiTestWorkspaceView from '@/views/cases/ApiTestWorkspaceView.vue'
import ApiCaseDetailView from '@/views/cases/ApiCaseDetailView.vue'

export default [
  {
    path: '/cases/requirements',
    name: 'Requirements',
    component: RequirementListView,
    meta: { titleKey: 'menu.casesRequirements', projectRequired: true },
  },
  {
    path: '/cases/requirements/:requirementId',
    name: 'RequirementDetail',
    component: RequirementDetailView,
    meta: { titleKey: 'menu.casesRequirements', projectRequired: true },
  },
  {
    path: '/cases/requirements/:requirementId/view',
    name: 'RequirementViewOnly',
    component: RequirementViewOnlyView,
    meta: { titleKey: 'page.requirements.viewDetail', projectRequired: true },
  },
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
