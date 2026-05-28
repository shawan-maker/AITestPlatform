<template>
  <el-dialog v-model="visible" :title="t('page.defects.transition')" width="420px">
    <el-form label-width="100px">
      <el-form-item :label="t('common.status')">
        <el-select v-model="form.status">
          <el-option v-for="s in DEFECT_STATUS" :key="s" :label="t(`defect.status.${s}`)" :value="s" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('page.defects.assignee')">
        <UserSearchPicker v-model="form.assignee_id" />
        <span class="optional-hint">{{ t('page.defects.assigneeOptional') }}</span>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" @click="submit">{{ t('common.confirm') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { DEFECT_STATUS } from '@/utils/constants'
import UserSearchPicker from '@/components/picker/UserSearchPicker.vue'

const props = defineProps({ modelValue: { type: Boolean, default: false } })
const emit = defineEmits(['update:modelValue', 'submit'])
const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const form = reactive({ status: 'open', assignee_id: null })

function submit() {
  emit('submit', { status: form.status, assignee_id: form.assignee_id || undefined })
}
</script>

<style scoped lang="scss">
.optional-hint {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
