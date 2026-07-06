<template>
  <tr class="env-param-row">
    <td class="col-content">
      <el-input
        v-model="local.name"
        :disabled="!canEdit || nameDisabled"
        @input="emitUpdate"
      />
    </td>
    <td v-if="showType" class="col-center">
      <el-select
        v-model="local.uiType"
        :disabled="!canEdit"
        size="small"
        style="width: 90px"
        @change="onTypeChange"
      >
        <el-option label="string" value="string" />
        <el-option label="file" value="file" />
      </el-select>
    </td>
    <td class="col-content">
      <EnvFilePicker
        v-if="local.uiType === 'file'"
        v-model="local.fileId"
        :project-id="projectId"
        @update:model-value="emitUpdate"
      />
      <el-input
        v-else
        v-model="local.stringValue"
        :disabled="!canEdit"
        :placeholder="local.encrypted ? '***' : ''"
        size="small"
        @input="emitUpdate"
      />
    </td>
    <td v-if="showEncrypt" class="col-center">
      <el-switch
        v-model="local.encrypted"
        :disabled="!canEdit || local.uiType === 'file'"
        @change="emitUpdate"
      />
    </td>
    <td class="col-content">
      <el-input
        v-model="local.remark"
        :disabled="!canEdit"
        @input="emitUpdate"
      />
    </td>
    <td v-if="canEdit" class="col-center actions">
      <ConfirmDelete @confirm="$emit('delete')">
        <el-button link type="danger" size="small">{{ t('common.delete') }}</el-button>
      </ConfirmDelete>
    </td>
  </tr>
</template>

<script setup>
import { reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import ConfirmDelete from '@/components/common/ConfirmDelete.vue'
import EnvFilePicker from '@/components/env/EnvFilePicker.vue'

const props = defineProps({
  row: { type: Object, required: true },
  canEdit: { type: Boolean, default: true },
  projectId: { type: Number, required: true },
  showType: { type: Boolean, default: true },
  showEncrypt: { type: Boolean, default: true },
  nameDisabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:row', 'delete'])

const { t } = useI18n()
const local = reactive({ ...props.row })

watch(
  () => props.row,
  (val) => Object.assign(local, val),
  { deep: true },
)

function emitUpdate() {
  emit('update:row', { ...local })
}

function onTypeChange() {
  if (local.uiType === 'file') {
    local.encrypted = false
    local.stringValue = ''
  } else {
    local.fileId = null
  }
  emitUpdate()
}
</script>

<style scoped>
.col-center {
  text-align: center;
}

.actions {
  white-space: nowrap;
}
</style>
