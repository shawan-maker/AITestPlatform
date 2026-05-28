import ProfileView from '@/views/profile/ProfileView.vue'

export default [
  {
    path: '/profile',
    name: 'Profile',
    component: ProfileView,
    meta: { titleKey: 'page.profile.title' },
  },
]
