<template>
  <div class="api-preview-panel">
    <div class="api-preview-panel__header">
      <span>{{ t('page.agent.previewTitle') }}</span>
      <el-button
        v-if="canEdit && baseCases.length"
        type="primary"
        size="small"
        @click="showConfirm = true"
      >{{ t('page.agent.confirmPreRun') }}</el-button>
    </div>

    <el-empty v-if="!baseCases.length" :description="t('page.agent.noPreview')" />

    <el-scrollbar v-else class="api-preview-panel__body">
      <el-checkbox-group v-model="selectedIndexes">
        <div v-for="(item, index) in baseCases" :key="index" class="case-card">
          <el-checkbox :label="index">
            <strong>{{ item.name || item.title || `Case ${index + 1}` }}</strong>
          </el-checkbox>
          <ul v-if="item.steps?.length" class="case-card__list">
            <li v-for="(step, si) in item.steps" :key="si">{{ step }}</li>
          </ul>
          <div v-if="item.expected?.length" class="case-card__expected">
            {{ item.expected.join('; ') }}
          </div>
        </div>
      </el-checkbox-group>
    </el-scrollbar>

    <ApiAgentConfirmDialog
      v-model="showConfirm"
      :catalogs="catalogs"
      :default-indexes="selectedIndexes"
      :interface-id="interfaceId"
      :loading="confirming"
      @submit="onConfirm"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import ApiAgentConfirmDialog from '@/components/agent/ApiAgentConfirmDialog.vue'

const props = defineProps({
  outputPayload: { type: Object, default: null },
  catalogs: { type: Array, default: () => [] },
  interfaceId: { type: Number, default: null },
  canEdit: { type: Boolean, default: false },
  confirming: { type: Boolean, default: false },
})

const emit = defineEmits(['confirm'])

const { t } = useI18n()
const showConfirm = ref(false)
const selectedIndexes = ref([])

const baseCases = computed(() => props.outputPayload?.base_cases ?? [])

watch(
  baseCases,
  (list) => {
    selectedIndexes.value = list.map((_, i) => i)
  },
  { immediate: true },
)

function onConfirm(payload) {
  emit('confirm', { ...payload, selected_indexes: payload.selected_indexes?.length ? payload.selected_indexes : selectedIndexes.value })
  showConfirm.value = false
}
</script>

<style scoped lang="scss">
.api-preview-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 480px;
}

.api-preview-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  font-weight: 600;
}

.api-preview-panel__body {
  flex: 1;
  padding: 12px;
}

.case-card {
  padding: 10px;
  margin-bottom: 8px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  font-size: 13px;

  &__list {
    margin: 6px 0 0;
    padding-left: 18px;
    color: var(--el-text-color-regular);
  }

  &__expected {
    margin-top: 6px;
    color: var(--el-text-color-secondary);
  }
}
</style>
