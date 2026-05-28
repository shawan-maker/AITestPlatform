<template>
  <div v-loading="loading" class="defect-detail-view app-card">
    <PageHeader :title="defect?.title || t('page.defects.title')">
      <template #actions>
        <el-button @click="router.push('/test/defects')">{{ t('common.back') }}</el-button>
        <el-button v-if="canEdit" @click="save">{{ t('common.save') }}</el-button>
        <el-button v-if="canEdit" type="primary" @click="showTransition = true">{{ t('page.defects.transition') }}</el-button>
      </template>
    </PageHeader>

    <el-form v-if="defect" :model="form" label-width="100px" style="max-width: 640px">
      <el-form-item :label="t('page.defects.title')"><el-input v-model="form.title" /></el-form-item>
      <el-form-item :label="t('page.defects.description')"><el-input v-model="form.description" type="textarea" :rows="4" /></el-form-item>
      <el-form-item :label="t('common.status')"><DefectStatusTag :status="defect.status" /></el-form-item>
    </el-form>

    <h3>{{ t('page.defects.comments') }}</h3>
    <el-timeline>
      <el-timeline-item v-for="item in defect?.history ?? []" :key="item.id || item.created_at">
        {{ item.content || item.message }}
      </el-timeline-item>
    </el-timeline>
    <el-input v-if="canEdit" v-model="comment" type="textarea" :rows="2" />
    <el-button v-if="canEdit" style="margin-top: 8px" @click="addComment">{{ t('page.defects.addComment') }}</el-button>

    <TransitionDefectDialog v-model="showTransition" @submit="doTransition" />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { addDefectComment, getDefect, transitionDefect, updateDefect } from '@/api/testManagement'
import { usePermission } from '@/composables/usePermission'
import PageHeader from '@/components/common/PageHeader.vue'
import DefectStatusTag from '@/components/defect/DefectStatusTag.vue'
import TransitionDefectDialog from '@/components/defect/TransitionDefectDialog.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { canEdit } = usePermission()
const defectId = computed(() => Number(route.params.defectId))

const loading = ref(false)
const defect = ref(null)
const form = reactive({ title: '', description: '' })
const comment = ref('')
const showTransition = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await getDefect(defectId.value)
    defect.value = res.data.data
    form.title = defect.value.title
    form.description = defect.value.description ?? ''
  } finally {
    loading.value = false
  }
}

async function save() {
  await updateDefect(defectId.value, { title: form.title, description: form.description })
  ElMessage.success(t('common.saved'))
  load()
}

async function doTransition(data) {
  await transitionDefect(defectId.value, data)
  ElMessage.success(t('common.saved'))
  showTransition.value = false
  load()
}

async function addComment() {
  await addDefectComment(defectId.value, { content: comment.value })
  comment.value = ''
  ElMessage.success(t('common.saved'))
  load()
}

onMounted(load)
</script>

<style scoped lang="scss">
h3 { margin: 24px 0 12px; font-size: 16px; }
</style>
