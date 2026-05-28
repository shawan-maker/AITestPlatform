<template>
  <el-dialog v-model="visible" :title="t('page.functional.create')" width="480px">
    <el-form :model="form" label-width="80px">
      <el-form-item :label="t('page.functional.caseName')" required>
        <el-input v-model="form.name" />
      </el-form-item>
      <el-form-item :label="t('page.functional.catalog')">
        <el-select v-model="form.catalog_id" filterable style="width: 100%">
          <el-option v-for="c in flatCatalogs" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item :label="t('page.functional.steps')">
        <el-input v-model="form.steps" type="textarea" :rows="5" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="submit">{{ t('common.create') }}</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  catalogs: { type: Array, default: () => [] },
  defaultCatalogId: { type: Number, default: null },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'submit'])
const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const form = reactive({ name: '', steps: '', catalog_id: null })

const flatCatalogs = computed(() => {
  const out = []
  function walk(nodes) {
    nodes.forEach((n) => { out.push(n); if (n.children) walk(n.children) })
  }
  walk(props.catalogs)
  return out
})

watch(visible, (v) => {
  if (v) {
    form.name = ''
    form.steps = ''
    form.catalog_id = props.defaultCatalogId
  }
})

function submit() {
  emit('submit', { ...form })
}
</script>
