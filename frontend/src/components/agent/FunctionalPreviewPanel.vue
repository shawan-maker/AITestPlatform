<template>
  <div class="functional-preview-panel">
    <div class="functional-preview-panel__header">
      <span>{{ t('page.agent.previewTitle') }}</span>
      <el-button
        v-if="canEdit && cases.length"
        type="primary"
        size="small"
        @click="showSave = true"
      >{{ t('page.agent.save') }}</el-button>
    </div>

    <el-empty v-if="!cases.length && !testPoints.length" :description="t('page.agent.noPreview')" />

    <el-scrollbar v-else class="functional-preview-panel__body">
      <div v-if="testPoints.length" class="section">
        <h4>{{ t('page.agent.testPoints') }}</h4>
        <ul>
          <li v-for="(tp, idx) in testPoints" :key="idx">
            {{ tp.test_point || tp.name || JSON.stringify(tp) }}
          </li>
        </ul>
      </div>

      <div v-if="cases.length" class="section">
        <h4>{{ t('page.agent.cases') }}</h4>
        <el-checkbox-group v-model="selectedIndexes">
          <div v-for="(item, index) in cases" :key="index" class="case-card">
            <el-checkbox :label="index">
              <strong>{{ item.case_name || item.name || `Case ${index + 1}` }}</strong>
            </el-checkbox>
            <div v-if="item.test_steps" class="case-card__steps">{{ item.test_steps }}</div>
            <div v-if="item.expected_result" class="case-card__expected">{{ item.expected_result }}</div>
          </div>
        </el-checkbox-group>
      </div>
    </el-scrollbar>

    <AgentSaveDialog
      v-model="showSave"
      :catalogs="catalogs"
      :case-count="cases.length"
      :default-indexes="selectedIndexes"
      :loading="saving"
      @submit="onSave"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AgentSaveDialog from '@/components/agent/AgentSaveDialog.vue'

const props = defineProps({
  outputPayload: { type: Object, default: null },
  catalogs: { type: Array, default: () => [] },
  canEdit: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
})

const emit = defineEmits(['save'])

const { t } = useI18n()
const showSave = ref(false)
const selectedIndexes = ref([])

const testPoints = computed(() => props.outputPayload?.test_points ?? [])
const cases = computed(() => props.outputPayload?.cases ?? [])

watch(
  cases,
  (list) => {
    selectedIndexes.value = list.map((_, i) => i)
  },
  { immediate: true },
)

function onSave(payload) {
  emit('save', payload)
  showSave.value = false
}
</script>

<style scoped lang="scss">
.functional-preview-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 480px;
}

.functional-preview-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  font-weight: 600;
}

.functional-preview-panel__body {
  flex: 1;
  padding: 12px;
}

.section {
  margin-bottom: 16px;

  h4 {
    margin: 0 0 8px;
    font-size: 14px;
  }

  ul {
    margin: 0;
    padding-left: 18px;
    font-size: 13px;
  }
}

.case-card {
  padding: 10px;
  margin-bottom: 8px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  font-size: 13px;

  &__steps,
  &__expected {
    margin-top: 6px;
    color: var(--el-text-color-secondary);
    white-space: pre-wrap;
  }
}
</style>
