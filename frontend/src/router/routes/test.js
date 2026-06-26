import SuiteListView from '@/views/test/SuiteListView.vue'
import SuiteDetailView from '@/views/test/SuiteDetailView.vue'
import SuiteReportView from '@/views/test/SuiteReportView.vue'
import TaskListView from '@/views/test/TaskListView.vue'
import TaskDetailView from '@/views/test/TaskDetailView.vue'
import TaskReportView from '@/views/test/TaskReportView.vue'
import DefectListView from '@/views/test/DefectListView.vue'
import DefectDetailView from '@/views/test/DefectDetailView.vue'

export default [
  {
    path: '/test/suites',
    name: 'TestSuites',
    component: SuiteListView,
    meta: { titleKey: 'menu.testSuites', projectRequired: true },
  },
  {
    path: '/test/suites/:suiteId',
    name: 'SuiteDetail',
    component: SuiteDetailView,
    meta: { titleKey: 'menu.testSuites', projectRequired: true },
  },
  {
    path: '/test/suites/:suiteId/report/:runId',
    name: 'SuiteReport',
    component: SuiteReportView,
    meta: { titleKey: 'menu.testSuites', projectRequired: true },
  },
  {
    path: '/test/tasks',
    name: 'TestTasks',
    component: TaskListView,
    meta: { titleKey: 'menu.testTasks', projectRequired: true },
  },
  {
    path: '/test/tasks/:taskId',
    name: 'TaskDetail',
    component: TaskDetailView,
    meta: { titleKey: 'menu.testTasks', projectRequired: true },
  },
  {
    path: '/test/tasks/:taskId/report/:runId',
    name: 'TaskReport',
    component: TaskReportView,
    meta: { titleKey: 'menu.testTasks', projectRequired: true },
  },
  {
    path: '/test/defects',
    name: 'TestDefects',
    component: DefectListView,
    meta: { titleKey: 'menu.testDefects', projectRequired: true },
  },
  {
    path: '/test/defects/:defectId',
    name: 'DefectDetail',
    component: DefectDetailView,
    meta: { titleKey: 'menu.testDefects', projectRequired: true },
  },
]
