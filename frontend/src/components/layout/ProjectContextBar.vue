<template>
  <ProjectSwitcher v-if="show" class="project-context-bar" />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import ProjectSwitcher from '@/components/layout/ProjectSwitcher.vue'

const route = useRoute()

const show = computed(() => route.meta.projectRequired === true)
</script>

<style scoped lang="scss">
.project-context-bar {
  width: 280px;
  max-width: 100%;
}
</style>
