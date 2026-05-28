import ProjectListView from '@/views/admin/ProjectListView.vue'
import ProjectDetailView from '@/views/admin/ProjectDetailView.vue'
import UserListView from '@/views/admin/UserListView.vue'
import UserDetailView from '@/views/admin/UserDetailView.vue'
import ProjectSettingsView from '@/views/project/ProjectSettingsView.vue'

export default [
  {
    path: '/admin/projects',
    name: 'AdminProjects',
    component: ProjectListView,
    meta: { titleKey: 'menu.adminProjects', superAdminOnly: true },
  },
  {
    path: '/admin/projects/:id',
    name: 'AdminProjectDetail',
    component: ProjectDetailView,
    meta: { titleKey: 'menu.adminProjects', superAdminOnly: true },
  },
  {
    path: '/admin/users',
    name: 'AdminUsers',
    component: UserListView,
    meta: { titleKey: 'menu.adminUsers', superAdminOnly: true },
  },
  {
    path: '/admin/users/:id',
    name: 'AdminUserDetail',
    component: UserDetailView,
    meta: { titleKey: 'menu.adminUsers', superAdminOnly: true },
  },
  {
    path: '/projects/:id/settings',
    name: 'ProjectSettings',
    component: ProjectSettingsView,
    meta: { titleKey: 'page.projectSettings.title', projectOwnerOrSuperAdmin: true },
  },
]
