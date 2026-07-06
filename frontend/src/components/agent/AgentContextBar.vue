<template>
  <div v-if="visible" class="agent-context-bar">
    <div class="agent-context-bar__inner">
      <el-icon><InfoFilled /></el-icon>
      <span>{{ contextText }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { InfoFilled } from '@element-plus/icons-vue'

const { t } = useI18n()

const props = defineProps({
  knowledgeDocTitle: { type: String, default: '' },
  inputRefType: { type: String, default: '' }, // 'requirement' | 'interface' | 'api_doc' | null
  interfaceMethod: { type: String, default: '' },
  interfacePath: { type: String, default: '' },
})

const visible = computed(() => !!(props.knowledgeDocTitle || props.inputRefType))

const contextText = computed(() => {
  if (props.knowledgeDocTitle) {
    return t('page.agent.contextDocBased', { title: props.knowledgeDocTitle })
  }
  if (props.inputRefType === 'interface' && props.interfacePath) {
    return t('page.agent.contextInterfaceBased', { name: `${props.interfaceMethod || ''} ${props.interfacePath}`.trim() })
  }
  if (props.inputRefType === 'api_doc') {
    return t('page.agent.contextPasteBased')
  }
  return ''
})
</script>

<style scoped lang="scss">
.agent-context-bar {
  position: sticky;
  top: 0;
  z-index: 5;
  background: rgba($color-primary, 0.04);
  border: 1px solid rgba($color-primary, 0.15);
  border-radius: 8px;
  margin-bottom: 12px;
}

.agent-context-bar__inner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.5;
  border-radius: inherit;
}
</style>
