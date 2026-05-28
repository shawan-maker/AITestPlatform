<template>
  <el-drawer v-model="visible" :title="isEdit ? t('page.apiCases.editInterface') : t('page.apiCases.createInterface')" size="420px">
    <el-form :model="form" label-width="80px">
      <el-form-item :label="t('page.apiCases.method')" required>
        <el-select v-model="form.method" style="width: 100%">
          <el-option v-for="m in HTTP_METHODS" :key="m" :label="m" :value="m" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('page.apiCases.path')" required>
        <el-input v-model="form.path" placeholder="/api/v1/example" />
      </el-form-item>
      <el-form-item :label="t('page.apiCases.summary')">
        <el-input v-model="form.summary" type="textarea" :rows="3" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="saving" @click="submit">{{ t('common.save') }}</el-button>
    </template>
  </el-drawer>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { createInterface, updateInterface } from '@/api/apiTest'
import { HTTP_METHODS } from '@/utils/constants'
import { useProjectScope } from '@/composables/useProjectScope'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  catalogId: { type: Number, default: null },
  interfaceData: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])
const { t } = useI18n()
const { withProjectParams } = useProjectScope()

const saving = ref(false)
const form = reactive({ method: 'GET', path: '', summary: '' })

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const isEdit = computed(() => !!props.interfaceData?.id)

watch(() => props.modelValue, (open) => {
  if (!open) return
  if (props.interfaceData) {
    form.method = props.interfaceData.method ?? 'GET'
    form.path = props.interfaceData.path ?? ''
    form.summary = props.interfaceData.summary ?? ''
  } else {
    form.method = 'GET'
    form.path = ''
    form.summary = ''
  }
})

async function submit() {
  if (!form.path?.trim()) {
    ElMessage.warning(t('validation.required'))
    return
  }
  saving.value = true
  try {
    if (isEdit.value) {
      await updateInterface(props.interfaceData.id, { ...form })
    } else {
      const params = withProjectParams()
      await createInterface({ ...form, catalog_id: props.catalogId }, params)
    }
    ElMessage.success(t('common.saved'))
    emit('saved')
    visible.value = false
  } finally {
    saving.value = false
  }
}
</script>
