<template>
  <div v-loading="pageLoading" class="project-settings-view app-card">
    <PageHeader :title="t('page.projectSettings.title')">
      <template #actions>
        <el-button @click="router.back()">{{ t('common.back') }}</el-button>
        <el-button v-if="auth.isSuperAdmin" type="danger" @click="showTransfer = true">
          {{ t('page.projectSettings.transferOwner') }}
        </el-button>
      </template>
    </PageHeader>

    <el-tabs v-model="activeTab">
      <el-tab-pane :label="t('page.projectSettings.tabBasic')" name="basic">
        <el-form :model="basicForm" label-width="100px" style="max-width: 560px">
          <el-form-item :label="t('page.admin.projects.name')">
            <el-input v-model="basicForm.name" />
          </el-form-item>
          <el-form-item :label="t('page.admin.projects.description')">
            <el-input v-model="basicForm.description" type="textarea" :rows="3" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="saving" @click="saveBasic">{{ t('common.save') }}</el-button>
          </el-form-item>
        </el-form>
      </el-tab-pane>
      <el-tab-pane :label="t('page.projectSettings.tabMembers')" name="members">
        <MemberPanel
          :members="members"
          :loading="membersLoading"
          @add="addMember"
          @update-role="updateMemberRole"
          @remove="removeMember"
        />
      </el-tab-pane>
      <el-tab-pane :label="t('page.projectSettings.tabModules')" name="modules">
        <ModulePanel
          :modules="modules"
          :loading="modulesLoading"
          @create="createModuleItem"
          @update="updateModuleItem"
          @delete="deleteModuleItem"
        />
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="showTransfer" :title="t('page.projectSettings.transferOwner')" width="400px">
      <el-form label-width="120px">
        <el-form-item :label="t('page.admin.users.userId')">
          <el-input-number v-model="newOwnerId" :min="1" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTransfer = false">{{ t('common.cancel') }}</el-button>
        <el-button type="danger" @click="doTransfer">{{ t('common.confirm') }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import {
  addMember as addMemberApi,
  createModule,
  deleteModule,
  getProject,
  listMembers,
  listModules,
  removeMember as removeMemberApi,
  transferOwner,
  updateMember,
  updateModule,
  updateProject,
} from '@/api/projects'
import { useAuthStore } from '@/stores/auth'
import PageHeader from '@/components/common/PageHeader.vue'
import MemberPanel from '@/components/admin/MemberPanel.vue'
import ModulePanel from '@/components/admin/ModulePanel.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const projectId = computed(() => Number(route.params.id))

const activeTab = ref('basic')
const pageLoading = ref(false)
const saving = ref(false)
const basicForm = reactive({ name: '', description: '' })
const members = ref([])
const membersLoading = ref(false)
const modules = ref([])
const modulesLoading = ref(false)
const showTransfer = ref(false)
const newOwnerId = ref(null)

async function loadProject() {
  pageLoading.value = true
  try {
    const res = await getProject(projectId.value)
    const data = res.data.data
    basicForm.name = data.name
    basicForm.description = data.description ?? ''
  } finally {
    pageLoading.value = false
  }
}

async function loadMembers() {
  membersLoading.value = true
  try {
    const res = await listMembers(projectId.value)
    members.value = res.data.data?.items ?? res.data.data ?? []
  } finally {
    membersLoading.value = false
  }
}

async function loadModules() {
  modulesLoading.value = true
  try {
    const res = await listModules(projectId.value)
    modules.value = res.data.data?.items ?? res.data.data ?? []
  } finally {
    modulesLoading.value = false
  }
}

async function saveBasic() {
  saving.value = true
  try {
    await updateProject(projectId.value, { name: basicForm.name, description: basicForm.description })
    ElMessage.success(t('common.saved'))
  } finally {
    saving.value = false
  }
}

async function addMember(data) {
  await addMemberApi(projectId.value, data)
  ElMessage.success(t('common.saved'))
  loadMembers()
}

async function updateMemberRole(row, role) {
  await updateMember(projectId.value, row.user_id ?? row.id, { role })
  ElMessage.success(t('common.saved'))
  loadMembers()
}

async function removeMember(row) {
  await removeMemberApi(projectId.value, row.user_id ?? row.id)
  ElMessage.success(t('common.deleted'))
  loadMembers()
}

async function createModuleItem(data) {
  await createModule(projectId.value, data)
  ElMessage.success(t('common.saved'))
  loadModules()
}

async function updateModuleItem(row, data) {
  await updateModule(projectId.value, row.id, data)
  ElMessage.success(t('common.saved'))
  loadModules()
}

async function deleteModuleItem(row) {
  await deleteModule(projectId.value, row.id)
  ElMessage.success(t('common.deleted'))
  loadModules()
}

async function doTransfer() {
  await transferOwner(projectId.value, newOwnerId.value)
  ElMessage.success(t('page.projectSettings.ownerTransferred'))
  showTransfer.value = false
  loadProject()
  loadMembers()
}

onMounted(() => {
  loadProject()
  loadMembers()
  loadModules()
})
</script>
