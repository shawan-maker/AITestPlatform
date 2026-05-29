<template>
  <ul v-if="catalogNodes.length" class="ui-tree-list">
    <li v-for="cat in catalogNodes" :key="cat.id" class="tree-node">
      <div
        class="ui-tree-node-row ui-tree-node-row--catalog"
        :class="{ 'is-active': selectedCatalogId === cat.id && !selectedEnvId }"
      >
        <span class="ui-tree-node-icon" aria-hidden="true">📁</span>
        <span class="ui-tree-node-label" @click="$emit('select-catalog', cat.id)">{{ cat.name }}</span>
        <el-dropdown
          v-if="canEdit"
          trigger="click"
          @command="(cmd) => $emit('catalog-command', cmd, cat.id)"
        >
          <TreeNodeMenuTrigger />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="catalog">{{ t('page.env.variables.addCatalog') }}</el-dropdown-item>
              <el-dropdown-item command="env">{{ t('page.env.variables.create') }}</el-dropdown-item>
              <el-dropdown-item command="delete" divided :disabled="!canDeleteCatalog(cat)">
                {{ t('common.delete') }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <ul v-if="hasChildren(cat)" class="ui-tree-nested">
        <li
          v-for="env in envsInCatalog(cat.id)"
          :key="'env-' + env.id"
          class="tree-node"
        >
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
        <EnvVariableTree
          v-if="cat.children?.length"
          :catalog-nodes="cat.children"
          :environments="environments"
          :selected-env-id="selectedEnvId"
          :selected-catalog-id="selectedCatalogId"
          :can-edit="canEdit"
          @select-catalog="(id) => $emit('select-catalog', id)"
          @select-env="(env) => $emit('select-env', env)"
          @catalog-command="(cmd, id) => $emit('catalog-command', cmd, id)"
          @env-command="(cmd, env) => $emit('env-command', cmd, env)"
        />
      </ul>
    </li>
  </ul>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import TreeNodeMenuTrigger from '@/components/common/TreeNodeMenuTrigger.vue'

defineOptions({ name: 'EnvVariableTree' })

const props = defineProps({
  catalogNodes: { type: Array, default: () => [] },
  environments: { type: Array, default: () => [] },
  selectedEnvId: { type: Number, default: null },
  selectedCatalogId: { type: Number, default: null },
  canEdit: { type: Boolean, default: true },
})

defineEmits(['select-catalog', 'select-env', 'catalog-command', 'env-command'])

const { t } = useI18n()

function envsInCatalog(catalogId) {
  return props.environments.filter((e) => e.catalog_id === catalogId)
}

function hasChildren(cat) {
  return envsInCatalog(cat.id).length > 0 || (cat.children?.length ?? 0) > 0
}

function canDeleteCatalog(cat) {
  return envsInCatalog(cat.id).length === 0 && !(cat.children?.length > 0)
}
</script>