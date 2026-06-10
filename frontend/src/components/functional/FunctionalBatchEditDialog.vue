<template>
  <el-dialog v-model="visible" :title="t('page.functional.batchEdit')" width="560px">
    <el-alert :title="t('page.functional.batchEditHint', { count: caseIds.length })" type="info" show-icon :closable="false" />
    <el-form label-width="120px" style="margin-top: 16px">
      <div class="form-row">
        <el-form-item :label="t('page.functional.caseCategory')" style="flex:1">
          <el-select v-model="form.case_category" clearable placeholder="-">
            <el-option value="functional" :label="t('page.functional.catFunctional')" />
            <el-option value="performance" :label="t('page.functional.catPerformance')" />
            <el-option value="security" :label="t('page.functional.catSecurity')" />
            <el-option value="compatibility" :label="t('page.functional.catCompatibility')" />
            <el-option value="usability" :label="t('page.functional.catUsability')" />
            <el-option value="other" :label="t('page.functional.catOther')" />
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
      <el-form-item :label="t('page.functional.catalog')">
        <CatalogSelectInline :catalog-nodes="catalogs" v-model="form.catalog_id" />
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
import CatalogSelectInline from './CatalogSelectInline.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  catalogs: { type: Array, default: () => [] },
  caseIds: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])
const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const catalogsRef = ref(props.catalogs || [])

watch(() => props.catalogs, (val) => {
  catalogsRef.value = val || []
})

const form = reactive({
  case_category: null,
  priority: null,
  catalog_id: null,
  preconditions: '',
  test_steps: '',
  test_data: '',
  expected_result: '',
})

const hasChanges = computed(() =>
  form.case_category !== null ||
  form.priority !== null ||
  form.catalog_id !== null ||
  !!form.preconditions ||
  !!form.test_steps ||
  !!form.test_data ||
  !!form.expected_result
)

watch(visible, (v) => {
  if (v) {
    Object.assign(form, {
      case_category: null, priority: null, catalog_id: null,
      preconditions: '', test_steps: '', test_data: '', expected_result: '',
    })
  }
})

function submit() {
  const payload = { case_ids: props.caseIds }
  if (form.case_category != null) payload.case_category = form.case_category
  if (form.priority != null) payload.priority = Number(form.priority)
  if (form.catalog_id != null) payload.catalog_id = form.catalog_id
  if (form.preconditions) payload.preconditions = form.preconditions
  if (form.test_steps) payload.test_steps = form.test_steps
  if (form.test_data) payload.test_data = form.test_data
  if (form.expected_result) payload.expected_result = form.expected_result
  emit('submit', payload)
}
</script>

<style scoped lang="scss">
.form-row {
  display: flex;
}
</style>
