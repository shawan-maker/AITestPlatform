<template>
  <el-dialog :close-on-click-modal="false" v-model="visible" :title="t('page.functional.batchCopy')" width="480px">
    <el-form label-width="100px">
      <el-form-item :label="t('page.functional.targetCatalog')" required>
        <CatalogSelectInline :catalog-nodes="catalogs" v-model="targetCatalogId" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="submit">
        {{ t('common.confirm') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import CatalogSelectInline from './CatalogSelectInline.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  catalogs: { type: Array, default: () => [] },
  caseIds: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'confirm'])
const { t } = useI18n()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const targetCatalogId = ref(null)

async function submit() {
  if (!targetCatalogId.value) {
    ElMessage.warning(t('page.functional.selectCatalogFirst'))
    return
  }
  emit('confirm', targetCatalogId.value)
}

watch(visible, (v) => {
  if (v) {
    targetCatalogId.value = null
  }
})
</script>
