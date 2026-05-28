<template>
  <el-alert v-if="visible" :title="title" type="info" show-icon :closable="false" class="async-job-banner">
    <template v-if="description" #default>{{ description }}</template>
  </el-alert>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: '' },
  description: { type: String, default: '' },
})
</script>

<style scoped lang="scss">
.async-job-banner {
  margin-bottom: 16px;
}
</style>
