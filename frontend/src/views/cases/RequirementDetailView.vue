<template>
  <div v-loading="loading" class="requirement-detail-view app-card">
    <PageHeader :title="req?.title || t('page.requirements.title')">
      <template #actions>
        <el-button @click="router.push('/cases/requirements')">{{ t('common.back') }}</el-button>
        <el-button v-if="canEdit" type="primary" @click="save">{{ t('common.save') }}</el-button>
        <ConfirmDelete v-if="canEdit" @confirm="remove">
          <el-button type="danger">{{ t('common.delete') }}</el-button>
        </ConfirmDelete>
      </template>
    </PageHeader>

    <el-form v-if="req" :model="form" label-width="100px" style="max-width: 640px">
      <el-form-item :label="t('page.requirements.title')"><el-input v-model="form.title" /></el-form-item>
      <el-form-item :label="t('page.requirements.description')"><el-input v-model="form.description" type="textarea" :rows="4" /></el-form-item>
    </el-form>

    <h3>{{ t('page.requirements.linkedCases') }}</h3>
    <AppTable :data="req?.linked_cases ?? []">
      <AppTableColumn prop="name" variant="content" :label="t('page.functional.caseName')" />
      <AppTableColumn actions variant="fixed" :label="t('common.actions')" :width="120">
        <template #default="{ row }">
          <el-button link type="primary" @click="router.push(`/cases/functional?caseId=${row.id}`)">{{ t('common.view') }}</el-button>
        </template>
      </AppTableColumn>
    </AppTable>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { deleteRequirement, getRequirement, updateRequirement } from '@/api/functional'
import { usePermission } from '@/composables/usePermission'
import AppTable from '@/components/common/AppTable.vue'
import AppTableColumn from '@/components/common/AppTableColumn.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { canEdit } = usePermission()
const reqId = computed(() => Number(route.params.requirementId))
const req = ref(null)
const loading = ref(false)
const form = reactive({ title: '', description: '' })

async function load() {
  loading.value = true
  try {
    const res = await getRequirement(reqId.value)
    req.value = res.data.data
    form.title = req.value.title
    form.description = req.value.description ?? ''
  } finally {
    loading.value = false
  }
}

async function save() {
  await updateRequirement(reqId.value, { title: form.title, description: form.description })
  ElMessage.success(t('common.saved'))
  load()
}

async function remove() {
  await deleteRequirement(reqId.value)
  ElMessage.success(t('common.deleted'))
  router.push('/cases/requirements')
}

onMounted(load)
</script>

<style scoped lang="scss">
h3 { margin: 24px 0 12px; font-size: 16px; }
</style>
