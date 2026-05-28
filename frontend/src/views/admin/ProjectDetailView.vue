<template>
  <div v-loading="loading" class="project-detail-view app-card">
    <PageHeader :title="project?.name || t('page.admin.projects.title')">
      <template #actions>
        <el-button @click="router.push('/admin/projects')">{{ t('common.back') }}</el-button>
        <el-button type="primary" @click="router.push(`/projects/${projectId}/settings`)">
          {{ t('page.projectSettings.title') }}
        </el-button>
      </template>
    </PageHeader>

    <el-descriptions v-if="project" :column="2" border>
      <el-descriptions-item :label="t('page.admin.projects.name')">{{ project.name }}</el-descriptions-item>
      <el-descriptions-item label="ID">{{ project.id }}</el-descriptions-item>
      <el-descriptions-item :label="t('page.admin.projects.description')" :span="2">{{ project.description || '—' }}</el-descriptions-item>
      <el-descriptions-item :label="t('page.projectSettings.owner')">{{ project.owner_username || '—' }}</el-descriptions-item>
      <el-descriptions-item :label="t('page.projectSettings.members')">{{ project.member_count ?? '—' }}</el-descriptions-item>
    </el-descriptions>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { getProject } from '@/api/projects'
import PageHeader from '@/components/common/PageHeader.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.id))
const project = ref(null)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await getProject(projectId.value)
    project.value = res.data.data
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
