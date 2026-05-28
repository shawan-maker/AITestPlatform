<template>
  <el-dialog v-model="visible" :title="t('page.admin.users.create')" width="480px" @closed="reset">
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
      <el-form-item :label="t('page.login.username')" prop="username">
        <el-input v-model="form.username" />
      </el-form-item>
      <el-form-item :label="t('page.register.email')" prop="email">
        <el-input v-model="form.email" />
      </el-form-item>
      <el-form-item :label="t('page.login.password')" prop="password">
        <el-input v-model="form.password" type="password" show-password />
      </el-form-item>
      <el-form-item :label="t('page.admin.users.superAdmin')">
        <el-switch v-model="form.is_super_admin" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="submit">{{ t('common.save') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])
const { t } = useI18n()
const formRef = ref()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const form = reactive({
  username: '',
  email: '',
  password: '',
  is_super_admin: false,
})

const rules = {
  username: [{ required: true, message: () => t('validation.required'), trigger: 'blur' }],
  email: [
    { required: true, message: () => t('validation.required'), trigger: 'blur' },
    { type: 'email', message: () => t('validation.emailInvalid'), trigger: 'blur' },
  ],
  password: [
    { required: true, message: () => t('validation.required'), trigger: 'blur' },
    { min: 6, max: 18, message: () => t('validation.passwordLength'), trigger: 'blur' },
  ],
}

function reset() {
  Object.assign(form, { username: '', email: '', password: '', is_super_admin: false })
  formRef.value?.resetFields()
}

async function submit() {
  await formRef.value?.validate()
  emit('submit', { ...form })
}
</script>
