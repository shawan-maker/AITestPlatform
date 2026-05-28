<template>
  <div class="profile-view app-card">
    <PageHeader :title="t('page.profile.title')" />
    <el-descriptions :column="1" border>
      <el-descriptions-item label="ID">{{ auth.user?.id }}</el-descriptions-item>
      <el-descriptions-item label="Username">{{ auth.user?.username }}</el-descriptions-item>
      <el-descriptions-item label="Email">{{ auth.user?.email }}</el-descriptions-item>
      <el-descriptions-item label="Super Admin">
        {{ auth.isSuperAdmin ? 'Yes' : 'No' }}
      </el-descriptions-item>
    </el-descriptions>
    <h3 class="profile-section">{{ t('page.profile.changePassword') }}</h3>
    <PasswordChangeForm :loading="changingPassword" @submit="changePassword" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { changeMyPassword } from '@/api/users'
import PageHeader from '@/components/common/PageHeader.vue'
import PasswordChangeForm from '@/components/common/PasswordChangeForm.vue'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const changingPassword = ref(false)

async function changePassword(data) {
  changingPassword.value = true
  try {
    await changeMyPassword(data)
    ElMessage.success(t('page.profile.passwordChanged'))
    await auth.logout()
    router.push('/login')
  } finally {
    changingPassword.value = false
  }
}
</script>

<style scoped lang="scss">
.profile-section {
  margin: 24px 0 12px;
  font-size: 16px;
}
</style>
