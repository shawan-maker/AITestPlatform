export const menuConfig = [
  {
    path: '/agent',
    titleKey: 'menu.agent',
    icon: 'Cpu',
    emphasis: 'featured',
  },
  {
    titleKey: 'menu.cases',
    icon: 'Document',
    children: [
      { path: '/cases/requirements', titleKey: 'menu.casesRequirements' },
      { path: '/cases/functional', titleKey: 'menu.casesFunctional' },
      { path: '/cases/api', titleKey: 'menu.casesApi' },
    ],
  },
  {
    titleKey: 'menu.test',
    icon: 'Monitor',
    children: [
      { path: '/test/suites', titleKey: 'menu.testSuites' },
      { path: '/test/tasks', titleKey: 'menu.testTasks' },
      { path: '/test/defects', titleKey: 'menu.testDefects' },
    ],
  },
  {
    titleKey: 'menu.docs',
    icon: 'FolderOpened',
    children: [{ path: '/docs/knowledge', titleKey: 'menu.docsKnowledge' }],
  },
  {
    titleKey: 'menu.env',
    icon: 'Management',
    children: [
      { path: '/env/variables', titleKey: 'menu.envVariables' },
      { path: '/env/databases', titleKey: 'menu.envDatabases' },
      { path: '/env/functions', titleKey: 'menu.envFunctions' },
      { path: '/env/files', titleKey: 'menu.envFiles' },
    ],
  },
  {
    path: '/projects',
    titleKey: 'menu.adminProjects',
    icon: 'OfficeBuilding',
  },
  {
    path: '/admin/users',
    titleKey: 'menu.adminUsers',
    icon: 'User',
    superAdminOnly: true,
    emphasis: 'admin',
  },
]

export function filterMenus(isSuperAdmin) {
  return menuConfig.filter((item) => !item.superAdminOnly || isSuperAdmin)
}
