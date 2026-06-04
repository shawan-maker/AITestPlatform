import { defineStore } from 'pinia'

/** 跨页面通知知识库列表/详情刷新（如需求页确认后隐藏「保存需求」） */
export const useKnowledgeStore = defineStore('knowledge', {
  state: () => ({
    refreshSeq: 0,
  }),
  actions: {
    requestRefresh() {
      this.refreshSeq += 1
    },
  },
})
