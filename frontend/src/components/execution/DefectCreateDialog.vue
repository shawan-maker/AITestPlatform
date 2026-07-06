<template>
  <el-dialog :close-on-click-modal="false" v-model="visible" :title="t('page.defects.create')" width="640px">
    <el-form label-width="100px">
      <el-form-item :label="t('page.defects.defectTitle')" required>
        <el-input v-model="form.title" />
      </el-form-item>
      <el-form-item :label="t('page.defects.category')">
        <el-select v-model="form.defect_category" style="width: 100%">
          <el-option v-for="(label, val) in defectCategoryMap" :key="val" :label="label" :value="val" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('page.defects.severity')">
        <el-select v-model="form.severity" style="width: 100%">
          <el-option v-for="(label, val) in defectSeverityMap" :key="val" :label="label" :value="val" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('page.defects.priority')">
        <el-select v-model="form.priority" style="width: 100%">
          <el-option v-for="(label, val) in defectPriorityMap" :key="val" :label="label" :value="val" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('page.defects.steps')">
        <el-input v-model="form.steps" type="textarea" :rows="4" />
      </el-form-item>
      <el-form-item :label="t('page.defects.rootCause')">
        <el-input v-model="form.root_cause" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item :label="t('page.defects.assignee')">
        <UserSearchPicker v-model="form.assignee_id" />
      </el-form-item>
      <el-form-item :label="t('page.defects.comment')">
        <el-input v-model="form.comment" type="textarea" :rows="2" :placeholder="t('page.defects.assigneeOptional')" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="submit">{{ t('common.save') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDefectSeverityMap, getDefectPriorityMap, getDefectCategoryMap } from '@/utils/constants'
import UserSearchPicker from '@/components/picker/UserSearchPicker.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  caseRunId: { type: [Number, String], default: null },
  defaultTitle: { type: String, default: '' },
  defaultSteps: { type: String, default: '' },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])
const { t } = useI18n()
const defectSeverityMap = computed(() => getDefectSeverityMap(t))
const defectPriorityMap = computed(() => getDefectPriorityMap(t))
const defectCategoryMap = computed(() => getDefectCategoryMap(t))

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const form = reactive({
  title: '',
  defect_category: 'other',
  severity: 'normal',
  priority: 'medium',
  steps: '',
  root_cause: '',
  assignee_id: null,
  comment: '',
})

watch(visible, (v) => {
  if (v) {
    form.title = props.defaultTitle
    form.steps = props.defaultSteps
    form.defect_category = 'other'
    form.severity = 'normal'
    form.priority = 'medium'
    form.root_cause = ''
    form.assignee_id = null
    form.comment = ''
  }
})

function submit() {
  if (!form.title?.trim()) return
  emit('submit', { case_run_id: props.caseRunId, ...form })
}
</script>
