import { PROJECT_ROLE_LABEL } from '@/utils/constants'

const BLOCKER_I18N_KEYS = {
  environments: 'page.projectSettings.blocker.environments',
  knowledge_workspaces: 'page.projectSettings.blocker.knowledgeWorkspaces',
  knowledge_documents: 'page.projectSettings.blocker.knowledgeDocuments',
  test_tasks: 'page.projectSettings.blocker.testTasks',
  test_suites: 'page.projectSettings.blocker.testSuites',
  ai_generation_sessions: 'page.projectSettings.blocker.aiSessions',
  api_interface_catalogs: 'page.projectSettings.blocker.apiCatalogs',
  api_interfaces: 'page.projectSettings.blocker.apiInterfaces',
  api_base_cases: 'page.projectSettings.blocker.apiBaseCases',
  api_test_cases: 'page.projectSettings.blocker.apiTestCases',
  functional_cases: 'page.projectSettings.blocker.functionalCases',
  requirement_docs: 'page.projectSettings.blocker.requirementDocs',
}

export function formatProjectBlockers(blockers, t) {
  if (!blockers || typeof blockers !== 'object') return ''
  return Object.entries(blockers)
    .filter(([, count]) => count > 0)
    .map(([key, count]) => {
      const label = t(BLOCKER_I18N_KEYS[key] ?? key)
      return `${label}(${count})`
    })
    .join('、')
}

export function extractBlockersFromError(error) {
  return error?.response?.data?.data?.blockers ?? error?.response?.data?.blockers ?? null
}

export { PROJECT_ROLE_LABEL }
