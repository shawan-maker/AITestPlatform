<template>
  <div v-loading="pageLoading" class="project-workspace app-card">
    <PageHeader :title="pageTitle" />

    <div class="page-toolbar">
      <el-button @click="router.push('/projects')">{{ t('common.back') }}</el-button>
    </div>

    <el-tabs v-model="activeTab" :before-leave="onBeforeTabLeave">
      <el-tab-pane :label="t('page.projectSettings.tabBasic')" name="basic">
        <el-descriptions v-if="!canEditBasic" :column="2" border class="project-workspace__desc">
          <el-descriptions-item :label="t('page.admin.projects.name')">{{ basicForm.name }}</el-descriptions-item>
          <el-descriptions-item label="ID">{{ projectId }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.projectSettings.admin')">{{ ownerUsername || '—' }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.projectSettings.members')">{{ memberCount ?? '—' }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.projectSettings.myRole')">{{ myRoleLabel || '—' }}</el-descriptions-item>
          <el-descriptions-item :label="t('page.admin.projects.description')" :span="2">{{ basicForm.description || '—' }}</el-descriptions-item>
        </el-descriptions>
        <SectionPanel v-else :title="t('page.projectSettings.tabBasic')">
          <el-form :model="basicForm" label-width="100px" class="detail-form">
            <el-form-item :label="t('page.admin.projects.name')">
              <el-input v-model="basicForm.name" />
            </el-form-item>
            <el-form-item :label="t('page.admin.projects.description')">
              <el-input v-model="basicForm.description" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item :label="t('page.projectSettings.admin')">{{ ownerUsername || '—' }}</el-form-item>
          </el-form>
          <FormActionBar :saving="saving" @save="saveBasic" @cancel="cancelBasic" />
        </SectionPanel>
      </el-tab-pane>
      <el-tab-pane v-if="canViewAdminTabs" :label="t('page.projectSettings.tabMembers')" name="members">
        <MemberPanel
          ref="memberPanelRef"
          :members="members"
          :loading="membersLoading"
          :saving="membersSaving"
          :can-edit="canEditBasic"
          :allow-admin="auth.isSuperAdmin"
          @add="addMember"
          @save-roles="saveMemberRoles"
          @remove="removeMember"
        />
      </el-tab-pane>
      <el-tab-pane v-if="canViewAdminTabs" :label="t('page.projectSettings.tabModules')" name="modules">
        <ModulePanel
          :modules="modules"
          :loading="modulesLoading"
          :can-edit="canEditBasic"
          @create="createModuleItem"
          @update="updateModuleItem"
          @delete="deleteModuleItem"
        />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  addMember as addMemberApi,
  createModule,
  deleteModule,
  getProject,
  listMembers,
  listModules,
  removeMember as removeMemberApi,
  updateMember,
  updateModule,
  updateProject,
} from '@/api/projects'
import { useAuthStore } from '@/stores/auth'
import { usePermissionStore } from '@/stores/permission'
import PageHeader from '@/components/common/PageHeader.vue'
import SectionPanel from '@/components/common/SectionPanel.vue'
import FormActionBar from '@/components/common/FormActionBar.vue'
import MemberPanel from '@/components/admin/MemberPanel.vue'
import ModulePanel from '@/components/admin/ModulePanel.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const permissionStore = usePermissionStore()
const projectId = computed(() => Number(route.params.id))

const activeTab = ref('basic')
const pageLoading = ref(false)
const saving = ref(false)
const membersSaving = ref(false)
const basicForm = reactive({ name: '', description: '' })
const ownerUsername = ref('')
const memberCount = ref(null)
const myRoleLabel = ref('')
const members = ref([])
const membersLoading = ref(false)
const modules = ref([])
const modulesLoading = ref(false)
const memberPanelRef = ref(null)
const basicSnapshot = ref(null)

const pageTitle = computed(() => basicForm.name || t('page.projectSettings.title'))
const canViewAdminTabs = computed(() => auth.isSuperAdmin || permissionStore.isOwner)
const canEditBasic = computed(() => auth.isSuperAdmin || permissionStore.isOwner)

async function onBeforeTabLeave(_newName, oldName) {
  if (oldName !== 'members' || !memberPanelRef.value?.hasPending) {
    return true
  }
  try {
    await ElMessageBox.confirm(
      t('page.projectSettings.membersUnsaved'),
      t('common.confirm'),
      { type: 'warning' },
    )
    memberPanelRef.value?.clearPending()
    return true
  } catch {
    return false
  }
}

async function loadProject() {
  pageLoading.value = true
  try {
    const res = await getProject(projectId.value)
    const data = res.data.data
    basicForm.name = data.name
    basicForm.description = data.description ?? ''
    basicSnapshot.value = { name: basicForm.name, description: basicForm.description }
    ownerUsername.value = data.owner_username
    memberCount.value = data.member_count ?? data.members?.length ?? null
    myRoleLabel.value = data.my_role_label ?? ''
    if (data.my_role != null && !auth.isSuperAdmin) {
      permissionStore.role = data.my_role
      permissionStore.roleLabel = data.my_role_label
    }
  } finally {
    pageLoading.value = false
  }
}

async function loadMembers() {
  membersLoading.value = true
  try {
    const res = await listMembers(projectId.value)
    members.value = res.data.data?.items ?? res.data.data ?? []
    memberCount.value = members.value.length
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
    basicSnapshot.value = { name: basicForm.name, description: basicForm.description }
    ElMessage.success(t('common.saved'))
  } finally {
    saving.value = false
  }
}

function cancelBasic() {
  if (!basicSnapshot.value) return
  basicForm.name = basicSnapshot.value.name
  basicForm.description = basicSnapshot.value.description
}

async function addMember(data) {
  await addMemberApi(projectId.value, data)
  ElMessage.success(t('common.saved'))
  loadMembers()
}

async function saveMemberRoles(changes) {
  membersSaving.value = true
  try {
    for (const { user_id, role } of changes) {
      await updateMember(projectId.value, user_id, { role })
    }
    ElMessage.success(t('common.saved'))
    memberPanelRef.value?.clearPending()
    await Promise.all([loadProject(), loadMembers()])
  } finally {
    membersSaving.value = false
  }
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

onMounted(async () => {
  if (!auth.isSuperAdmin) {
    await permissionStore.loadRoleForProject(projectId.value)
  }
  await loadProject()
  if (canViewAdminTabs.value) {
    await Promise.all([loadMembers(), loadModules()])
  }
})
</script>

<style scoped lang="scss">
.project-workspace__desc {
  margin-bottom: 16px;
}

.detail-form {
  max-width: 560px;
  margin: 0 auto;
}
</style>
