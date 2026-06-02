<template>
  <el-drawer v-model="visible" :title="t('page.env.db.testLogs')" size="60%">
    <DbTestLogTable v-if="connectionId" :connection-id="connectionId" />
  </el-drawer>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import DbTestLogTable from '@/components/env/DbTestLogTable.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  connectionId: { type: Number, default: null },
})

const emit = defineEmits(['update:modelValue'])
const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})
</script>
