<template>
  <div ref="containerRef" class="split-view" :class="{ 'split-view--vertical': vertical }">
    <template v-if="!useDrawerLayout">
      <div class="split-view__left" :style="leftStyle">
        <slot name="left" />
      </div>
      <div class="split-view__resizer" @mousedown="startDrag" />
      <div class="split-view__right">
        <slot name="right" />
      </div>
    </template>

    <template v-else>
      <div class="split-view__drawer-layout">
        <div class="split-view__drawer-bar">
          <el-button size="small" @click="drawerOpen = true">
            {{ drawerTitle || t('common.openSidebar') }}
          </el-button>
        </div>
        <el-drawer
          v-model="drawerOpen"
          direction="ltr"
          :size="drawerSize"
          :with-header="false"
          class="split-view-drawer"
        >
          <div class="split-view__drawer-body">
            <slot name="left" />
          </div>
        </el-drawer>
        <div class="split-view__right split-view__right--full">
          <slot name="right" />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useMediaQuery } from '@/composables/useMediaQuery'

const props = defineProps({
  initialWidth: { type: Number, default: 280 },
  minWidth: { type: Number, default: 240 },
  maxWidth: { type: Number, default: 480 },
  vertical: { type: Boolean, default: false },
  drawerOnNarrow: { type: Boolean, default: true },
  drawerTitle: { type: String, default: '' },
})

const { t } = useI18n()
const isNarrow = useMediaQuery('(max-width: 991px)')

const leftWidth = ref(props.initialWidth)
const dragging = ref(false)
const containerRef = ref(null)
const drawerOpen = ref(false)
const drawerSize = ref('50%')

const useDrawerLayout = computed(() => props.drawerOnNarrow && isNarrow.value && !props.vertical)

const leftStyle = computed(() => ({
  width: `${leftWidth.value}px`,
  minWidth: `${props.minWidth}px`,
  maxWidth: `${props.maxWidth}px`,
}))

function updateDrawerSize() {
  const el = containerRef.value
  const width = el?.clientWidth ?? window.innerWidth
  drawerSize.value = `${Math.round(width * 0.5)}px`
}

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

watch(useDrawerLayout, (v) => {
  if (v) updateDrawerSize()
  else drawerOpen.value = false
})

onMounted(() => {
  updateDrawerSize()
  window.addEventListener('resize', updateDrawerSize)
})

onUnmounted(() => {
  onMouseUp()
  window.removeEventListener('resize', updateDrawerSize)
})

onBeforeUnmount(onMouseUp)
</script>

<style scoped lang="scss">
.split-view {
  display: flex;
  flex: 1;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  gap: 0;
}

.split-view__left {
  flex-shrink: 0;
  overflow-x: hidden;
  overflow-y: auto;
  border-right: 1px solid var(--el-border-color-lighter);
  padding: 8px 12px;
  box-sizing: border-box;
  align-self: stretch;
  min-height: 0;
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
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow-x: hidden;
  overflow-y: auto;
  padding: 8px 16px;
  box-sizing: border-box;

  &--full {
    padding-top: 0;
  }
}

.split-view__drawer-layout {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  min-width: 0;
}

.split-view__drawer-bar {
  flex-shrink: 0;
  padding: 0 0 8px;
}

.split-view__drawer-body {
  height: 100%;
  overflow: auto;
  padding: 8px 12px;
  box-sizing: border-box;
}
</style>

<style lang="scss">
.split-view-drawer .el-drawer__body {
  padding: 0;
  overflow: hidden;
}
</style>
