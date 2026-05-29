<template>
  <div v-if="visible" class="ui-form-actions">
    <el-button type="primary" :loading="saving" @click="$emit('save')">
      {{ t('common.save') }}
    </el-button>
    <el-button :disabled="saving" @click="$emit('cancel')">
      {{ t('common.cancel') }}
    </el-button>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

defineProps({
  saving: { type: Boolean, default: false },
  visible: { type: Boolean, default: true },
})

defineEmits(['save', 'cancel'])

const { t } = useI18n()
</script>
