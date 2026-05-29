import UserListView from '@/views/admin/UserListView.vue'
import UserDetailView from '@/views/admin/UserDetailView.vue'

export default [
  {
    path: '/admin/projects',
    redirect: '/projects',
  },
  {
    path: '/admin/projects/:id',
    redirect: (to) => ({ path: `/projects/${to.params.id}` }),
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
]
