<template>
  <div class="ui-tree-sidebar env-variable-sidebar">
    <el-input
      :model-value="keyword"
      :placeholder="t('page.env.variables.searchPlaceholder')"
      clearable
      style="margin-bottom: 12px"
      @update:model-value="$emit('update:keyword', $event)"
    />

    <div
      class="ui-tree-node-row ui-tree-node-row--global"
      :class="{ 'is-active': selection === 'global' }"
      @click="$emit('select-global')"
    >
      <span class="ui-tree-node-icon" aria-hidden="true">🌐</span>
      <span class="ui-tree-node-label">{{ t('page.env.variables.global') }}</span>
    </div>

    <div class="env-section">
      <div class="ui-tree-section-header">
        <span>{{ t('page.env.variables.envSection') }}</span>
        <el-dropdown
          v-if="canEdit"
          trigger="click"
          @command="(cmd) => $emit('section-command', cmd)"
        >
          <TreeNodeMenuTrigger />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="catalog">{{ t('page.env.variables.addCatalog') }}</el-dropdown-item>
              <el-dropdown-item command="env">{{ t('page.env.variables.create') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <EnvVariableTree
        :catalog-nodes="catalogNodes"
        :environments="filteredEnvironments"
        :selected-env-id="selectedEnvId"
        :selected-catalog-id="selectedCatalogId"
        :can-edit="canEdit"
        @select-catalog="(id) => $emit('select-catalog', id)"
        @select-env="(env) => $emit('select-env', env)"
        @catalog-command="(cmd, id) => $emit('catalog-command', cmd, id)"
        @env-command="(cmd, env) => $emit('env-command', cmd, env)"
      />

      <ul v-if="rootEnvironments.length" class="ui-tree-list">
        <li v-for="env in rootEnvironments" :key="env.id">
          <div
            class="ui-tree-node-row ui-tree-node-row--env"
            :class="{ 'is-active': selectedEnvId === env.id }"
          >
            <span class="ui-tree-node-icon" aria-hidden="true">📄</span>
            <span class="ui-tree-node-label" @click="$emit('select-env', env)">{{ env.env_name }}</span>
            <el-dropdown
              v-if="canEdit"
              trigger="click"
              @command="(cmd) => $emit('env-command', cmd, env)"
            >
              <TreeNodeMenuTrigger />
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="copy">{{ t('page.env.variables.copy') }}</el-dropdown-item>
                  <el-dropdown-item command="export">{{ t('page.env.variables.export') }}</el-dropdown-item>
                  <el-dropdown-item command="import">{{ t('page.env.variables.import') }}</el-dropdown-item>
                  <el-dropdown-item command="delete" divided>{{ t('common.delete') }}</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import EnvVariableTree from '@/components/env/EnvVariableTree.vue'
import TreeNodeMenuTrigger from '@/components/common/TreeNodeMenuTrigger.vue'

const props = defineProps({
  catalogNodes: { type: Array, default: () => [] },
  environments: { type: Array, default: () => [] },
  keyword: { type: String, default: '' },
  selection: { type: [String, Number], default: 'global' },
  selectedEnvId: { type: Number, default: null },
  selectedCatalogId: { type: Number, default: null },
  canEdit: { type: Boolean, default: true },
})

defineEmits([
  'update:keyword',
  'select-global',
  'select-catalog',
  'select-env',
  'section-command',
  'catalog-command',
  'env-command',
])

const { t } = useI18n()

const filteredEnvironments = computed(() => {
  const kw = props.keyword.trim().toLowerCase()
  if (!kw) return props.environments
  return props.environments.filter((e) => e.env_name?.toLowerCase().includes(kw))
})

const rootEnvironments = computed(() =>
  filteredEnvironments.value.filter((e) => !e.catalog_id),
)
</script>

<style scoped>
.env-section {
  margin-top: 8px;
}
</style>
