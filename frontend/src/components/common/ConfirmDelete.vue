<template>
  <span @click="open">
    <slot />
  </span>
</template>

<script setup>
import { ElMessageBox } from 'element-plus'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  title: { type: String, default: '' },
  message: { type: String, default: '' },
  confirmText: { type: String, default: '' },
})

const emit = defineEmits(['confirm'])
const { t } = useI18n()

async function open() {
  try {
    await ElMessageBox.confirm(
      props.message || t('common.deleteConfirm'),
      props.title || t('common.confirmDelete'),
      {
        type: 'warning',
        confirmButtonText: props.confirmText || t('common.confirm'),
        cancelButtonText: t('common.cancel'),
      },
    )
    emit('confirm')
  } catch {
    /* cancelled */
  }
}
</script>
