<template>
  <div v-loading="loading" class="defect-detail-view app-card">
    <PageHeader :title="defect?.title || t('page.defects.title')">
      <template #actions>
        <el-button @click="router.push('/test/defects')">{{ t('common.back') }}</el-button>
        <el-button v-if="canEdit" type="primary" @click="showTransition = true">{{ t('page.defects.transition') }}</el-button>
      </template>
    </PageHeader>

    <SectionPanel v-if="defect" :title="t('page.defects.title')">
      <el-form :model="form" label-width="100px" class="detail-form">
        <el-form-item :label="t('page.defects.title')"><el-input v-model="form.title" /></el-form-item>
        <el-form-item :label="t('page.defects.description')"><el-input v-model="form.description" type="textarea" :rows="4" /></el-form-item>
        <el-form-item :label="t('common.status')"><DefectStatusTag :status="defect.status" /></el-form-item>
      </el-form>
      <FormActionBar v-if="canEdit" :saving="saving" @save="save" @cancel="cancelEdit" />
    </SectionPanel>

    <SectionPanel :title="t('page.defects.comments')">
      <el-timeline>
        <el-timeline-item v-for="item in defect?.history ?? []" :key="item.id || item.created_at">
          {{ item.content || item.message }}
        </el-timeline-item>
      </el-timeline>
      <el-input v-if="canEdit" v-model="comment" type="textarea" :rows="2" />
      <div v-if="canEdit" class="comment-actions">
        <el-button type="primary" :loading="commentSaving" @click="addComment">{{ t('page.defects.addComment') }}</el-button>
        <el-button @click="comment = ''">{{ t('common.cancel') }}</el-button>
      </div>
    </SectionPanel>

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
import SectionPanel from '@/components/common/SectionPanel.vue'
import FormActionBar from '@/components/common/FormActionBar.vue'
import DefectStatusTag from '@/components/defect/DefectStatusTag.vue'
import TransitionDefectDialog from '@/components/defect/TransitionDefectDialog.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const { canEdit } = usePermission()
const defectId = computed(() => Number(route.params.defectId))

const loading = ref(false)
const saving = ref(false)
const commentSaving = ref(false)
const defect = ref(null)
const form = reactive({ title: '', description: '' })
const snapshot = ref(null)
const comment = ref('')
const showTransition = ref(false)

function takeSnapshot() {
  snapshot.value = { title: form.title, description: form.description ?? '' }
}

async function load() {
  loading.value = true
  try {
    const res = await getDefect(defectId.value)
    defect.value = res.data.data
    form.title = defect.value.title
    form.description = defect.value.description ?? ''
    takeSnapshot()
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    await updateDefect(defectId.value, { title: form.title, description: form.description })
    ElMessage.success(t('common.saved'))
    await load()
  } finally {
    saving.value = false
  }
}

function cancelEdit() {
  if (!snapshot.value) return
  form.title = snapshot.value.title
  form.description = snapshot.value.description
}

async function doTransition(data) {
  await transitionDefect(defectId.value, data)
  ElMessage.success(t('common.saved'))
  showTransition.value = false
  load()
}

async function addComment() {
  if (!comment.value.trim()) return
  commentSaving.value = true
  try {
    await addDefectComment(defectId.value, { content: comment.value })
    comment.value = ''
    ElMessage.success(t('common.saved'))
    load()
  } finally {
    commentSaving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.detail-form {
  max-width: 640px;
  margin: 0 auto;
}

.comment-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 12px;
}
</style>
