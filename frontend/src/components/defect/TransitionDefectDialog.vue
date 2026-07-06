<template>
  <el-dialog :close-on-click-modal="false" v-model="visible" :title="t('page.defects.transition')" width="520px">
    <el-form label-width="100px">
      <el-form-item :label="t('common.status')">
        <el-select v-model="form.status">
          <el-option v-for="s in validStatuses" :key="s" :label="defectStatusMap[s]?.label || s" :value="s" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('page.defects.assignee')">
        <UserSearchPicker v-model="form.assignee_id" />
        <span class="optional-hint">{{ t('page.defects.assigneeOptional') }}</span>
      </el-form-item>
      <el-form-item v-if="form.status === 'resolved'" :label="t('page.defects.rootCause')" required>
        <el-input v-model="form.root_cause" type="textarea" :rows="2" />
      </el-form-item>
      <el-form-item :label="t('page.defects.comment')">
        <el-input v-model="form.comment" type="textarea" :rows="3" :placeholder="t('page.defects.transitionCommentPlaceholder')" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" @click="submit">{{ t('common.confirm') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDefectStatusMap, DEFECT_ALLOWED_TRANSITIONS } from '@/utils/constants'
import UserSearchPicker from '@/components/picker/UserSearchPicker.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  currentStatus: { type: String, default: 'init' },
})
const emit = defineEmits(['update:modelValue', 'submit'])
const { t } = useI18n()

const defectStatusMap = computed(() => getDefectStatusMap(t))

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const validStatuses = computed(() => {
  return DEFECT_ALLOWED_TRANSITIONS[props.currentStatus] || []
})

const form = reactive({ status: '', assignee_id: null, root_cause: '', comment: '' })

watch(visible, (v) => {
  if (v) {
    var targets = validStatuses.value
    form.status = targets[0] || ''
    form.assignee_id = null
    form.root_cause = ''
    form.comment = ''
  }
})

function submit() {
  if (!form.status) return
  if (form.status === 'resolved' && !form.root_cause?.trim()) {
    return
  }
  emit('submit', {
    status: form.status,
    assignee_id: form.assignee_id || undefined,
    root_cause: form.root_cause?.trim() || undefined,
    comment: form.comment?.trim() || undefined,
  })
}
</script>

<style scoped lang="scss">
.optional-hint {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
