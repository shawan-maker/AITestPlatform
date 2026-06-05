<template>
  <el-select
    v-model="innerValue"
    filterable
    remote
    clearable
    reserve-keyword
    :remote-method="searchUsers"
    :loading="loading"
    :placeholder="placeholder || t('page.login.username')"
    @change="onChange"
  >
    <el-option
      v-for="u in options"
      :key="u.id"
      :label="`${u.username} (${u.email})`"
      :value="u.id"
    />
  </el-select>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { lookupUsers } from '@/api/users'

const props = defineProps({
  modelValue: { type: Number, default: null },
  placeholder: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()

const innerValue = ref(props.modelValue)
const options = ref([])
const loading = ref(false)

watch(
  () => props.modelValue,
  (v) => { innerValue.value = v },
)

async function searchUsers(query) {
  loading.value = true
  try {
    const res = await lookupUsers(query?.trim() || undefined, 1, 30)
    options.value = res.data.data?.items ?? []
  } catch {
    options.value = []
  } finally {
    loading.value = false
  }
}

function onChange(v) {
  emit('update:modelValue', v ?? null)
}

searchUsers('')
</script>
