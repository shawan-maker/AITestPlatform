<template>
  <el-form ref="formRef" :model="form" :rules="rules" label-width="96px" class="register-form">
    <el-form-item :label="t('page.register.username')" prop="username">
      <el-input v-model="form.username" autocomplete="username" />
    </el-form-item>
    <el-form-item :label="t('page.register.email')" prop="email">
      <el-input v-model="form.email" autocomplete="email" />
    </el-form-item>
    <el-form-item :label="t('page.register.password')" prop="password">
      <el-input v-model="form.password" type="password" show-password autocomplete="new-password" />
    </el-form-item>
    <el-form-item :label="t('page.register.verifyPassword')" prop="verify_password">
      <el-input
        v-model="form.verify_password"
        type="password"
        show-password
        autocomplete="new-password"
      />
    </el-form-item>
    <el-form-item>
      <div class="auth-actions">
        <el-button type="primary" :loading="loading" class="auth-actions__primary" @click="onSubmit">
          {{ t('page.register.submit') }}
        </el-button>
        <el-button @click="onReset">{{ t('page.register.reset') }}</el-button>
      </div>
    </el-form-item>
    <div class="auth-footer">
      <router-link to="/login">{{ t('page.register.toLogin') }}</router-link>
    </div>
  </el-form>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { register } from '@/api/auth'

const { t } = useI18n()
const router = useRouter()
const formRef = ref()
const loading = ref(false)

const form = reactive({
  username: '',
  email: '',
  password: '',
  verify_password: '',
})

const rules = {
  username: [{ required: true, message: () => t('validation.required'), trigger: 'blur' }],
  email: [
    { required: true, message: () => t('validation.required'), trigger: 'blur' },
    { type: 'email', message: () => t('validation.emailInvalid'), trigger: 'blur' },
  ],
  password: [
    { required: true, message: () => t('validation.required'), trigger: 'blur' },
    {
      min: 6,
      max: 18,
      message: () => t('validation.passwordLength'),
      trigger: 'blur',
    },
  ],
  verify_password: [
    { required: true, message: () => t('validation.required'), trigger: 'blur' },
    {
      validator: (_rule, value, callback) => {
        if (value !== form.password) {
          callback(new Error(t('validation.passwordMismatch')))
        } else {
          callback()
        }
      },
      trigger: 'blur',
    },
  ],
}

async function onSubmit() {
  await formRef.value?.validate()
  loading.value = true
  try {
    await register({ ...form })
    ElMessage.success(t('page.register.registerSuccess'))
    router.push('/login')
  } finally {
    loading.value = false
  }
}

function onReset() {
  formRef.value?.resetFields()
  form.username = ''
  form.email = ''
  form.password = ''
  form.verify_password = ''
}
</script>

<style scoped lang="scss">
.register-form {
  font-size: 15px;

  :deep(.el-form-item__label) {
    font-size: 15px;
  }

  :deep(.el-input__wrapper) {
    min-height: 48px;
    font-size: 15px;
  }

  :deep(.el-button) {
    font-size: 15px;
    min-height: 42px;
  }
}

.auth-actions {
  display: flex;
  gap: 12px;
  width: 100%;

  &__primary {
    flex: 1;
  }
}

.auth-footer {
  text-align: center;
  font-size: 14px;
}
</style>
