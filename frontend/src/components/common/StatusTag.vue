<template>
  <el-tag :type="tagType" size="small">{{ label }}</el-tag>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, default: '' },
  map: { type: Object, default: () => ({}) },
})

const tagType = computed(() => props.map[props.status]?.type || 'info')
const label = computed(() => props.map[props.status]?.label || props.status || '—')
</script>
