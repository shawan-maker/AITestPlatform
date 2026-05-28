<template>
  <div ref="containerRef" class="split-view" :class="{ 'split-view--vertical': vertical }">
    <div class="split-view__left" :style="leftStyle">
      <slot name="left" />
    </div>
    <div
      class="split-view__resizer"
      @mousedown="startDrag"
    />
    <div class="split-view__right">
      <slot name="right" />
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  initialWidth: { type: Number, default: 280 },
  minWidth: { type: Number, default: 240 },
  maxWidth: { type: Number, default: 480 },
  vertical: { type: Boolean, default: false },
})

const leftWidth = ref(props.initialWidth)
const dragging = ref(false)
const containerRef = ref(null)

const leftStyle = computed(() => ({
  width: `${leftWidth.value}px`,
  minWidth: `${props.minWidth}px`,
  maxWidth: `${props.maxWidth}px`,
}))

function onMouseMove(e) {
  if (!dragging.value || !containerRef.value) return
  const rect = containerRef.value.getBoundingClientRect()
  const next = e.clientX - rect.left
  leftWidth.value = Math.min(props.maxWidth, Math.max(props.minWidth, next))
}

function onMouseUp() {
  dragging.value = false
  document.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('mouseup', onMouseUp)
}

function startDrag() {
  dragging.value = true
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
}

onBeforeUnmount(onMouseUp)
</script>

<style scoped lang="scss">
.split-view {
  display: flex;
  flex: 1;
  min-height: 0;
  height: 100%;
  gap: 0;
}

.split-view__left {
  flex-shrink: 0;
  overflow: auto;
  border-right: 1px solid var(--el-border-color-lighter);
}

.split-view__resizer {
  width: 4px;
  cursor: col-resize;
  background: transparent;
  flex-shrink: 0;

  &:hover {
    background: rgba($color-primary, 0.2);
  }
}

.split-view__right {
  flex: 1;
  min-width: 0;
  overflow: auto;
}
</style>
