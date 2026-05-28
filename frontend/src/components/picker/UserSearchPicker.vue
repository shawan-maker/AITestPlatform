<template>
  <el-select
    v-if="auth.isSuperAdmin"
    v-model="innerValue"
    filterable
    remote
    reserve-keyword
    :remote-method="searchUsers"
    :loading="loading"
    :placeholder="t('page.projectSettings.searchUser')"
    style="width: 100%"
    @change="onChange"
  >
    <el-option
      v-for="u in options"
      :key="u.id"
      :label="`${u.username} (${u.email})`"
      :value="u.id"
    />
  </el-select>
  <el-input-number
    v-else
    v-model="innerValue"
    :min="1"
    style="width: 100%"
    :placeholder="t('page.admin.users.userId')"
    @change="onChange"
  />
</template>

<script setup>
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { listUsers } from '@/api/users'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  modelValue: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()
const auth = useAuthStore()

const innerValue = ref(props.modelValue)
const options = ref([])
const loading = ref(false)

watch(
  () => props.modelValue,
  (v) => { innerValue.value = v },
)

async function searchUsers(query) {
  if (!query?.trim()) {
    options.value = []
    return
  }
  loading.value = true
  try {
    const res = await listUsers({ username: query.trim(), page: 1, page_size: 20, is_active: true })
    options.value = res.data.data?.items ?? []
  } catch {
    options.value = []
  } finally {
    loading.value = false
  }
}

function onChange(v) {
  emit('update:modelValue', v)
}
</script>
