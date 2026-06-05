<template>
  <el-tag :type="tagType" size="small">{{ label }}</el-tag>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, default: 3 },
})

const tagType = computed(() => {
  const map = { 1: 'danger', 2: 'warning', 3: 'info', 4: 'info' }
  return map[props.value] || 'info'
})
const label = computed(() => {
  const map = { 1: 'P0', 2: 'P1', 3: 'P2', 4: 'P3' }
  return map[props.value] || `P${props.value}`
})
</script>
