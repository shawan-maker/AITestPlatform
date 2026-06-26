<template>
  <el-alert v-if="progress" :title="progress.status" type="info" show-icon>
    <template #default>
      {{ progress.finished ?? 0 }} / {{ progress.total ?? 0 }}
    </template>
  </el-alert>
</template>

<script setup>
defineProps({ progress: { type: Object, default: null } })
</script>
