import ProjectListView from '@/views/admin/ProjectListView.vue'
import ProjectWorkspaceView from '@/views/project/ProjectWorkspaceView.vue'

export default [
  {
    path: '/projects',
    name: 'Projects',
    component: ProjectListView,
    meta: { titleKey: 'menu.adminProjects' },
  },
  {
    path: '/projects/:id',
    name: 'ProjectDetail',
    component: ProjectWorkspaceView,
    meta: { titleKey: 'page.projectSettings.title', projectMemberRequired: true },
  },
  {
    path: '/projects/:id/settings',
    redirect: (to) => ({ path: `/projects/${to.params.id}` }),
  },
]
