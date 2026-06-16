<template>
  <el-dialog :close-on-click-modal="false"
    v-model="visible"
    :title="t('page.functional.create')"
    :width="dialogWidth"
    :top="dialogTop"
    :class="dialogClass"
  >
    <el-form ref="formRef" :model="form" label-width="100px" :rules="formRules">
      <el-form-item :label="t('page.functional.caseName')" prop="case_name" required>
        <el-input v-model="form.case_name" maxlength="255" show-word-limit />
      </el-form-item>
      <div class="form-row">
        <el-form-item :label="t('page.functional.caseCategory')" prop="case_category" required style="flex:1">
          <el-select v-model="form.case_category">
            <el-option value="functional" :label="t('page.functional.catFunctional')" />
            <el-option value="performance" :label="t('page.functional.catPerformance')" />
            <el-option value="security" :label="t('page.functional.catSecurity')" />
            <el-option value="compatibility" :label="t('page.functional.catCompatibility')" />
            <el-option value="usability" :label="t('page.functional.catUsability')" />
            <el-option value="other" :label="t('page.functional.catOther')" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('page.functional.priority')" prop="priority" required style="flex:1; margin-left: 12px">
          <el-select v-model="form.priority">
            <el-option label="P0 (紧急)" :value="1" />
            <el-option label="P1 (高)" :value="2" />
            <el-option label="P2 (中)" :value="3" />
            <el-option label="P3 (低)" :value="4" />
          </el-select>
        </el-form-item>
      </div>
      <el-form-item :label="t('page.knowledge.module')">
        <ModuleSelect v-model="form.module_id" clearable />
      </el-form-item>
      <el-form-item :label="t('page.functional.catalog')" prop="catalog_id" required>
        <CatalogSelectInline :catalog-nodes="catalogs" v-model="form.catalog_id" />
      </el-form-item>
      <el-form-item :label="t('page.functional.preconditions')">
        <el-input
          v-model="form.preconditions"
          type="textarea"
          :rows="3"
          :placeholder="t('page.functional.preconditionsPlaceholder', { default: '' })"
        />
      </el-form-item>
      <el-form-item :label="t('page.functional.steps')">
        <el-input
          v-model="form.test_steps"
          type="textarea"
          :rows="textareaRows"
          :style="{ maxHeight: `${bodyMaxHeight}px` }"
        />
      </el-form-item>
      <el-form-item :label="t('page.functional.testData')">
        <el-input
          v-model="form.test_data"
          type="textarea"
          :rows="3"
          :placeholder="t('page.functional.testDataPlaceholder', { default: '' })"
        />
      </el-form-item>
      <el-form-item :label="t('page.functional.expectedResult')">
        <el-input
          v-model="form.expected_result"
          type="textarea"
          :rows="3"
          :placeholder="t('page.functional.expectedResultPlaceholder', { default: '' })"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="submit">{{ t('common.create') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import ModuleSelect from '@/components/tree/ModuleSelect.vue'
import CatalogSelectInline from './CatalogSelectInline.vue'
import { useContentDialog } from '@/composables/useContentDialog'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  catalogs: { type: Array, default: () => [] },
  defaultCatalogId: { type: Number, default: null },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])
const { t } = useI18n()
const { dialogWidth, dialogTop, dialogClass, bodyMaxHeight } = useContentDialog(260)

const textareaRows = computed(() => Math.max(5, Math.floor(bodyMaxHeight.value / 28)))
const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
const formRef = ref(null)

const formRules = {
  case_name: [{ required: true, message: () => t('validation.requiredField', { field: t('page.functional.caseName') }), trigger: 'blur' }],
  case_category: [{ required: true, message: () => t('validation.requiredField', { field: t('page.functional.caseCategory') }), trigger: 'change' }],
  priority: [{ required: true, message: () => t('validation.requiredField', { field: t('page.functional.priority') }), trigger: 'change' }],
  catalog_id: [{ required: true, message: () => t('validation.requiredField', { field: t('page.functional.catalog') }), trigger: 'change' }],
}

const form = reactive({
  case_name: '',
  case_category: 'functional',
  priority: 3,
  module_id: null,
  catalog_id: null,
  preconditions: '',
  test_steps: '',
  test_data: '',
  expected_result: '',
  jira_issue_key: '',
})

async function submit() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  emit('submit', { ...form })
}

watch(visible, (v) => {
  if (v) {
    Object.assign(form, {
      case_name: '', case_category: 'functional', priority: 3,
      module_id: null, catalog_id: props.defaultCatalogId ?? null,
      preconditions: '', test_steps: '', test_data: '',
      expected_result: '', jira_issue_key: '',
    })
  }
})
</script>

<style scoped lang="scss">
.form-row {
  display: flex;
}
</style>
