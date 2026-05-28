import EnvVariableWorkspaceView from '@/views/env/EnvVariableWorkspaceView.vue'
import EnvVariableDetailView from '@/views/env/EnvVariableDetailView.vue'
import DbConnectionListView from '@/views/env/DbConnectionListView.vue'
import FunctionFileListView from '@/views/env/FunctionFileListView.vue'
import UploadedFileListView from '@/views/env/UploadedFileListView.vue'

export default [
  {
    path: '/env/variables',
    name: 'EnvVariables',
    component: EnvVariableWorkspaceView,
    meta: { titleKey: 'menu.envVariables', projectRequired: true },
  },
  {
    path: '/env/variables/:environmentId',
    name: 'EnvVariableDetail',
    component: EnvVariableDetailView,
    meta: { titleKey: 'menu.envVariables', projectRequired: true },
  },
  {
    path: '/env/databases',
    name: 'EnvDatabases',
    component: DbConnectionListView,
    meta: { titleKey: 'menu.envDatabases', projectRequired: false },
  },
  {
    path: '/env/functions',
    name: 'EnvFunctions',
    component: FunctionFileListView,
    meta: { titleKey: 'menu.envFunctions', projectRequired: true },
  },
  {
    path: '/env/files',
    name: 'EnvFiles',
    component: UploadedFileListView,
    meta: { titleKey: 'menu.envFiles', projectRequired: true },
  },
]
