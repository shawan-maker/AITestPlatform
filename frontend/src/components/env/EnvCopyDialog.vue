<template>
  <el-dialog v-model="visible" :title="t('page.env.variables.copy')" width="420px">
    <el-form label-width="100px">
      <el-form-item :label="t('common.name')">
        <el-input v-model="name" :placeholder="t('page.env.variables.copyNameHint')" />
      </el-form-item>
    </el-form>
    <el-alert v-if="resultName" type="success" :title="t('page.env.variables.copyResult', { name: resultName })" show-icon />
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="submit">{{ t('common.confirm') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { copyEnvironment } from '@/api/environment'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  environmentId: { type: Number, default: null },
  defaultName: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'copied'])
const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const name = ref('')
const loading = ref(false)
const resultName = ref('')

watch(visible, (v) => {
  if (v) {
    name.value = props.defaultName ? `${props.defaultName}_copy` : ''
    resultName.value = ''
  }
})

async function submit() {
  loading.value = true
  try {
    const res = await copyEnvironment(props.environmentId, { env_name: name.value || undefined })
    resultName.value = res.data.data?.env_name ?? res.data.data?.name ?? name.value
    ElMessage.success(t('common.saved'))
    emit('copied', res.data.data)
    visible.value = false
  } finally {
    loading.value = false
  }
}
</script>
