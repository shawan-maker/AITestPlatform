<template>
  <el-form
    ref="formRef"
    :model="form"
    :rules="rules"
    label-width="88px"
    class="login-form"
    @submit.prevent="onSubmit"
  >
    <el-form-item :label="t('page.login.username')" prop="username">
      <el-input v-model="form.username" autocomplete="username" />
    </el-form-item>
    <el-form-item :label="t('page.login.password')" prop="password">
      <el-input
        v-model="form.password"
        type="password"
        show-password
        autocomplete="current-password"
        @keyup.enter="onSubmit"
      />
    </el-form-item>
    <el-form-item>
      <div class="auth-actions">
        <el-button type="primary" :loading="loading" class="auth-actions__primary" @click="onSubmit">
          {{ t('page.login.submit') }}
        </el-button>
        <el-button @click="onReset">{{ t('page.login.reset') }}</el-button>
      </div>
    </el-form-item>
    <div class="auth-footer">
      <router-link to="/register">{{ t('page.login.toRegister') }}</router-link>
    </div>
  </el-form>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useProjectStore } from '@/stores/project'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const projectStore = useProjectStore()

const formRef = ref()
const loading = ref(false)
const form = reactive({
  username: '',
  password: '',
})

const rules = {
  username: [{ required: true, message: () => t('validation.required'), trigger: 'blur' }],
  password: [{ required: true, message: () => t('validation.required'), trigger: 'blur' }],
}

async function onSubmit() {
  await formRef.value?.validate()
  loading.value = true
  try {
    await auth.login(form.username, form.password)
    await projectStore.fetchProjects()
    const redirect = route.query.redirect || '/agent'
    router.push(String(redirect))
  } catch (e) {
    ElMessage.error(e.message || t('page.login.failed'))
  } finally {
    loading.value = false
  }
}

function onReset() {
  formRef.value?.resetFields()
  form.username = ''
  form.password = ''
}
</script>

<style scoped lang="scss">
.login-form {
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
  font-size: 15px;
}
</style>
