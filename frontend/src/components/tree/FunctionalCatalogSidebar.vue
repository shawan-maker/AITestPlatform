<template>
  <CatalogTreeSidebar
    :keyword="keyword"
    :show-search="false"
    :root-label="t('page.functional.allCases')"
    :is-root-active="selectedCatalogId == null"
    :add-catalog-label="t('page.functional.addCatalog')"
    :can-edit="canEdit"
    @select-root="$emit('select-root')"
    @section-command="$emit('section-command', $event)"
  >
    <FunctionalCatalogTreeNode
      v-if="catalogNodes.length"
      :catalog-nodes="catalogNodes"
      :selected-catalog-id="selectedCatalogId"
      :expanded-catalog-ids="expandedCatalogIds"
      :can-edit="canEdit"
      @select-catalog="(id) => $emit('select-catalog', id)"
      @toggle-expand="(id) => $emit('toggle-expand', id)"
      @catalog-command="(cmd, node) => $emit('catalog-command', cmd, node)"
      @catalog-drop="(payload) => $emit('catalog-drop', payload)"
    />
  </CatalogTreeSidebar>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import CatalogTreeSidebar from '@/components/tree/CatalogTreeSidebar.vue'
import FunctionalCatalogTreeNode from '@/components/tree/FunctionalCatalogTreeNode.vue'

defineProps({
  catalogNodes: { type: Array, default: () => [] },
  keyword: { type: String, default: '' },
  selectedCatalogId: { type: Number, default: null },
  expandedCatalogIds: { type: Array, default: () => [] },
  canEdit: { type: Boolean, default: true },
})

defineEmits(['select-root', 'select-catalog', 'toggle-expand', 'section-command', 'catalog-command', 'catalog-drop'])

const { t } = useI18n()
</script>
