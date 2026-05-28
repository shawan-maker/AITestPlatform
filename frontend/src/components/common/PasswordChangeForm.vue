<template>
  <el-form ref="formRef" :model="form" :rules="rules" label-width="120px" @submit.prevent>
    <el-form-item :label="t('page.profile.oldPassword')" prop="old_password">
      <el-input v-model="form.old_password" type="password" show-password autocomplete="current-password" />
    </el-form-item>
    <el-form-item :label="t('page.profile.newPassword')" prop="new_password">
      <el-input v-model="form.new_password" type="password" show-password autocomplete="new-password" />
    </el-form-item>
    <el-form-item :label="t('page.profile.confirmPassword')" prop="confirm_password">
      <el-input v-model="form.confirm_password" type="password" show-password autocomplete="new-password" />
    </el-form-item>
    <el-form-item>
      <el-button type="primary" :loading="loading" @click="submit">{{ t('common.save') }}</el-button>
    </el-form-item>
  </el-form>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['submit'])
const { t } = useI18n()
const formRef = ref()

const form = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const rules = {
  old_password: [{ required: true, message: () => t('validation.required'), trigger: 'blur' }],
  new_password: [
    { required: true, message: () => t('validation.required'), trigger: 'blur' },
    { min: 6, max: 18, message: () => t('validation.passwordLength'), trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: () => t('validation.required'), trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== form.new_password) callback(new Error(t('validation.passwordMismatch')))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

async function submit() {
  await formRef.value?.validate()
  emit('submit', { old_password: form.old_password, new_password: form.new_password })
}
</script>
