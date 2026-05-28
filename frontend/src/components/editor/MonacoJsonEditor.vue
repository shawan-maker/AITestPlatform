<template>
  <div ref="containerRef" class="monaco-json-editor" :style="{ height: `${height}px` }" />
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as monaco from 'monaco-editor'
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import jsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker'

self.MonacoEnvironment = {
  getWorker(_, label) {
    if (label === 'json') return new jsonWorker()
    return new editorWorker()
  },
}

const props = defineProps({
  modelValue: { type: String, default: '' },
  readOnly: { type: Boolean, default: false },
  height: { type: Number, default: 280 },
  language: { type: String, default: 'json' },
})

const emit = defineEmits(['update:modelValue'])

const containerRef = ref(null)
let editor = null
let syncing = false

function formatValue(val) {
  if (!val) return ''
  if (props.language !== 'json') return String(val)
  if (typeof val === 'object') {
    try {
      return JSON.stringify(val, null, 2)
    } catch {
      return String(val)
    }
  }
  const s = String(val)
  try {
    return JSON.stringify(JSON.parse(s), null, 2)
  } catch {
    return s
  }
}

onMounted(() => {
  editor = monaco.editor.create(containerRef.value, {
    value: formatValue(props.modelValue),
    language: props.language,
    theme: 'vs',
    readOnly: props.readOnly,
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    automaticLayout: true,
    tabSize: 2,
  })
  editor.onDidChangeModelContent(() => {
    if (syncing) return
    emit('update:modelValue', editor.getValue())
  })
})

watch(
  () => props.modelValue,
  (val) => {
    if (!editor) return
    const next = formatValue(val)
    if (editor.getValue() !== next) {
      syncing = true
      editor.setValue(next)
      syncing = false
    }
  },
)

watch(
  () => props.readOnly,
  (ro) => editor?.updateOptions({ readOnly: ro }),
)

onBeforeUnmount(() => {
  editor?.dispose()
  editor = null
})
</script>

<style scoped lang="scss">
.monaco-json-editor {
  width: 100%;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: $radius-md;
  overflow: hidden;
}
</style>
