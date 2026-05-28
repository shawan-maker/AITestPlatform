<template>
  <el-alert v-if="progress" :title="progress.status" type="info" show-icon>
    <template #default>
      {{ progress.completed_count ?? 0 }} / {{ progress.total_count ?? 0 }}
    </template>
  </el-alert>
</template>

<script setup>
defineProps({ progress: { type: Object, default: null } })
</script>
