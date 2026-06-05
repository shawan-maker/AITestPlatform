<template>
  <el-dialog v-model="visible" :title="t('page.functional.batchEdit')" width="560px">
    <el-alert :title="t('page.functional.batchEditHint', { count: caseIds.length })" type="info" show-icon :closable="false" />
    <el-form label-width="120px" style="margin-top: 16px">
      <div class="form-row">
        <el-form-item :label="t('page.functional.type')" style="flex:1">
          <el-select v-model="form.type" clearable placeholder="-">
            <el-option value="functional" :label="t('page.functional.typeFunctional')" />
            <el-option value="ui" :label="'UI'" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('page.functional.priority')" style="flex:1; margin-left: 12px">
          <el-select v-model="form.priority" clearable placeholder="-">
            <el-option label="P0" :value="1" />
            <el-option label="P1" :value="2" />
            <el-option label="P2" :value="3" />
            <el-option label="P3" :value="4" />
          </el-select>
        </el-form-item>
      </div>
      <el-form-item :label="t('page.functional.execResult')">
        <el-select v-model="form.exec_result" clearable placeholder="-">
          <el-option value="pending" :label="t('status.exec.pending')" />
          <el-option value="passed" :label="t('status.exec.passed')" />
          <el-option value="failed" :label="t('status.exec.failed')" />
          <el-option value="blocked" :label="t('status.exec.blocked')" />
          <el-option value="skipped" :label="t('status.exec.skipped')" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('page.functional.catalog')">
        <CatalogSelectInline :catalog-nodes="catalogsRef" v-model="form.catalog_id" />
      </el-form-item>
      <el-form-item :label="t('page.functional.preconditions')">
        <el-input v-model="form.preconditions" type="textarea" :rows="2" placeholder="-" />
      </el-form-item>
      <el-form-item :label="t('page.functional.steps')">
        <el-input v-model="form.test_steps" type="textarea" :rows="2" placeholder="-" />
      </el-form-item>
      <el-form-item :label="t('page.functional.testData')">
        <el-input v-model="form.test_data" type="textarea" :rows="2" placeholder="-" />
      </el-form-item>
      <el-form-item :label="t('page.functional.expectedResult')">
        <el-input v-model="form.expected_result" type="textarea" :rows="2" placeholder="-" />
      </el-form-item>
      <el-form-item :label="t('page.functional.jiraKey')">
        <el-input v-model="form.jira_issue_key" maxlength="50" placeholder="-" clearable />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :disabled="!hasChanges" :loading="loading" @click="submit">
        {{ t('common.save') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  caseIds: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])
const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const catalogsRef = ref([])

const form = reactive({
  type: null,
  priority: null,
  exec_result: null,
  catalog_id: null,
  preconditions: '',
  test_steps: '',
  test_data: '',
  expected_result: '',
  jira_issue_key: '',
})

const hasChanges = computed(() =>
  form.type !== null ||
  form.priority !== null ||
  form.exec_result !== null ||
  form.catalog_id !== null ||
  !!form.preconditions ||
  !!form.test_steps ||
  !!form.test_data ||
  !!form.expected_result ||
  !!form.jira_issue_key
)

// 内联目录选择器
const CatalogSelectInline = {
  props: ['catalogNodes', 'modelValue'],
  emits: ['update:modelValue'],
  template: `
    <el-select :modelValue filterable clearable style="width:100%" @change="$emit(\'update:modelValue\', $event)">
      <el-option
        v-for="c in flatNodes" :key="c.id" :label="c.name || t('page.functional.allCases')" :value="c.id"
      />
    </el-select>`,
  setup(props, { emit }) {
    const flatNodes = ref([])
    function walk(nodes) {
      nodes.forEach((n) => { flatNodes.value.push(n); if (n.children?.length) walk(n.children) })
    }
    watch(() => props.catalogNodes, (val) => {
      flatNodes.value = []
      if (val?.length) walk(val)
    }, { immediate: true })
    return { flatNodes }
  },
}

watch(visible, (v) => {
  if (v) {
    Object.assign(form, {
      type: null, priority: null, exec_result: null, catalog_id: null,
      preconditions: '', test_steps: '', test_data: '', expected_result: '', jira_issue_key: '',
    })
  }
})

function submit() {
  const payload = { case_ids: props.caseIds }
  if (form.type != null) payload.type = form.type
  if (form.priority != null) payload.priority = Number(form.priority)
  if (form.exec_result != null) payload.exec_result = form.exec_result
  if (form.catalog_id != null) payload.catalog_id = form.catalog_id
  if (form.preconditions) payload.preconditions = form.preconditions
  if (form.test_steps) payload.test_steps = form.test_steps
  if (form.test_data) payload.test_data = form.test_data
  if (form.expected_result) payload.expected_result = form.expected_result
  if (form.jira_issue_key) payload.jira_issue_key = form.jira_issue_key
  emit('submit', payload)
}
</script>

<style scoped lang="scss">
.form-row {
  display: flex;
}
</style>
