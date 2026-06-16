<template>
  <el-dialog :close-on-click-modal="false"
    v-model="visible"
    :title="isEdit ? t('page.env.db.edit') : t('page.env.db.create')"
    width="560px"
    @closed="reset"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
      <el-form-item :label="t('page.env.db.connectionName')" prop="connection_name">
        <el-input v-model="form.connection_name" maxlength="50" />
      </el-form-item>
      <el-form-item :label="t('page.env.db.serverName')" prop="server_name">
        <el-input v-model="form.server_name" maxlength="50" />
      </el-form-item>
      <el-form-item :label="t('page.env.db.dbType')" prop="db_type">
        <el-select v-model="form.db_type" style="width: 100%">
          <el-option label="MySQL" value="mysql" />
          <el-option label="SQL Server" value="sqlserver" />
          <el-option label="Oracle" value="oracle" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('page.env.db.host')" prop="host">
        <el-input v-model="form.host" />
      </el-form-item>
      <el-form-item :label="t('page.env.db.port')" prop="port">
        <el-input-number v-model="form.port" :min="1" :max="65535" style="width: 100%" />
      </el-form-item>
      <el-form-item :label="t('page.env.db.username')" prop="username">
        <el-input v-model="form.username" />
      </el-form-item>
      <el-form-item :label="t('page.env.db.password')" prop="password">
        <el-input
          v-model="form.password"
          type="password"
          show-password
          :placeholder="isEdit ? t('page.env.db.passwordKeep') : ''"
        />
      </el-form-item>
      <el-form-item :label="t('page.env.db.databaseName')">
        <el-input v-model="form.database_name" />
      </el-form-item>
      <el-form-item :label="t('common.description')">
        <el-input v-model="form.description" type="textarea" :rows="2" maxlength="255" />
      </el-form-item>
      <el-form-item :label="t('page.env.db.bindEnvironments')">
        <el-select v-model="form.environment_ids" multiple filterable style="width: 100%">
          <el-option
            v-for="env in envOptions"
            :key="env.id"
            :label="env.env_name"
            :value="env.id"
          />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="submit">{{ t('common.save') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { createDbConnection, getDbConnection, listEnvironments, updateDbConnection } from '@/api/environment'
import { useProjectScope } from '@/composables/useProjectScope'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  connectionId: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])
const { t } = useI18n()
const { withProjectParams } = useProjectScope()
const formRef = ref()
const loading = ref(false)
const envOptions = ref([])

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const isEdit = computed(() => !!props.connectionId)

const defaultForm = () => ({
  connection_name: '',
  server_name: '',
  db_type: 'mysql',
  host: '',
  port: 3306,
  username: '',
  password: '',
  database_name: '',
  description: '',
  environment_ids: [],
})

const form = reactive(defaultForm())

const rules = {
  connection_name: [{ required: true, message: () => t('validation.required'), trigger: 'blur' }],
  server_name: [{ required: true, message: () => t('validation.required'), trigger: 'blur' }],
  db_type: [{ required: true, message: () => t('validation.required'), trigger: 'change' }],
  host: [{ required: true, message: () => t('validation.required'), trigger: 'blur' }],
  port: [{ required: true, message: () => t('validation.required'), trigger: 'blur' }],
  username: [{ required: true, message: () => t('validation.required'), trigger: 'blur' }],
  password: [{
    validator: (_rule, value, callback) => {
      if (!isEdit.value && !value) callback(new Error(t('validation.required')))
      else callback()
    },
    trigger: 'blur',
  }],
}

async function loadEnvOptions() {
  const params = withProjectParams({ page: 1, page_size: 100 })
  if (!params) return
  const res = await listEnvironments(params)
  envOptions.value = res.data.data?.items ?? res.data.data ?? []
}

async function loadConnection() {
  if (!props.connectionId) {
    Object.assign(form, defaultForm())
    return
  }
  const res = await getDbConnection(props.connectionId)
  const c = res.data.data
  Object.assign(form, {
    connection_name: c.connection_name ?? '',
    server_name: c.server_name ?? '',
    db_type: c.db_type ?? 'mysql',
    host: c.config?.host ?? c.host ?? '',
    port: c.config?.port ?? 3306,
    username: c.config?.username ?? '',
    password: '',
    database_name: c.config?.database_name ?? '',
    description: c.description ?? '',
    environment_ids: [...(c.environment_ids ?? [])],
  })
}

watch(visible, async (v) => {
  if (v) {
    await loadEnvOptions()
    await loadConnection()
  }
})

function reset() {
  formRef.value?.resetFields()
  Object.assign(form, defaultForm())
}

function buildPayload() {
  const payload = {
    connection_name: form.connection_name,
    server_name: form.server_name,
    db_type: form.db_type,
    description: form.description || null,
    environment_ids: form.environment_ids,
    config: {
      host: form.host,
      port: form.port,
      username: form.username,
      database_name: form.database_name || null,
    },
  }
  if (form.password) payload.config.password = form.password
  else if (!isEdit.value) payload.config.password = ''
  return payload
}

async function submit() {
  await formRef.value?.validate()
  loading.value = true
  try {
    const payload = buildPayload()
    if (isEdit.value) {
      const params = withProjectParams()
      await updateDbConnection(props.connectionId, payload, params ?? {})
    } else {
      if (!payload.config.password) payload.config.password = ''
      const params = withProjectParams()
      await createDbConnection(payload, params ?? {})
    }
    emit('saved')
    visible.value = false
  } finally {
    loading.value = false
  }
}
</script>
