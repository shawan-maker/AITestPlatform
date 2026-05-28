import KnowledgeListView from '@/views/docs/KnowledgeListView.vue'
import KnowledgeDetailView from '@/views/docs/KnowledgeDetailView.vue'

export default [
  {
    path: '/docs/knowledge',
    name: 'Knowledge',
    component: KnowledgeListView,
    meta: { titleKey: 'menu.docsKnowledge', projectRequired: true },
  },
  {
    path: '/docs/knowledge/:documentId',
    name: 'KnowledgeDetail',
    component: KnowledgeDetailView,
    meta: { titleKey: 'menu.docsKnowledge', projectRequired: true },
  },
]
