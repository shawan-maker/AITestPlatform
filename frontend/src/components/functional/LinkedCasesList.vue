<template>
  <div v-if="loading" class="text-center">
    <el-skeleton :rows="3" animated />
  </div>
  <el-table v-else :data="data" size="small" max-height="400">
    <el-table-column prop="case_name" :label="t('page.functional.caseName')" show-overflow-tooltip min-width="160" />
    <el-table-column prop="priority" :label="t('page.functional.priority')" width="70" align="center">
      <template #default="{ row }"><PriorityTag :value="row.priority" /></template>
    </el-table-column>
    <el-table-column :label="t('page.functional.execResult')" width="100" align="center">
      <template #header>{{ t('page.functional.execResult') }}</template>
      <template #default="{ row }"><ExecResultTag :value="row.exec_result" /></template>
    </el-table-column>
    <el-table-column :label="t('common.actions')" width="110">
      <template #header>{{ t('common.actions') }}</template>
      <template #default="{ row }">
        <div class="table-cell-actions">
          <el-button link type="primary" size="small" @click="$emit('open-case', row)">{{ t('page.functional.viewDetail') }}</el-button>
        </div>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { getCase as listCasesApi } from '@/api/functional'
import PriorityTag from '@/components/tags/PriorityTag.vue'
import ExecResultTag from '@/components/tags/ExecResultTag.vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  requirementId: { type: Number, required: true },
})
const emit = defineEmits(['open-case'])

const { t } = useI18n()
const loading = ref(false)
const data = ref([])

async function load() {
  loading.value = true
  try {
    const res = await listCasesApi({ requirement_id: props.requirementId, page_size: 100 })
    data.value = res.data.data?.items ?? []
  } catch {
    data.value = []
  } finally {
    loading.value = false
  }
}

watch(() => props.requirementId, load, { immediate: true })
</script>

<style scoped lang="scss">
.text-center {
  padding: 12px;
}
</style>
