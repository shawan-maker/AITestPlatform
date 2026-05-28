<template>
  <ul class="catalog-tree">
    <li
      v-for="node in nodes"
      :key="node.id"
      :class="{ active: node.id === modelValue }"
      @click="$emit('update:modelValue', node.id)"
    >
      {{ node.name }}
      <CatalogTree
        v-if="node.children?.length"
        :nodes="node.children"
        :model-value="modelValue"
        @update:model-value="$emit('update:modelValue', $event)"
      />
    </li>
  </ul>
</template>

<script setup>
defineProps({
  nodes: { type: Array, default: () => [] },
  modelValue: { type: [Number, null], default: null },
})
defineEmits(['update:modelValue'])
</script>

<style scoped lang="scss">
.catalog-tree {
  list-style: none;
  margin: 0;
  padding: 0 0 0 12px;

  li {
    padding: 6px 8px;
    cursor: pointer;
    border-radius: $radius-sm;

    &.active, &:hover {
      background: rgba($color-primary, 0.08);
      color: $color-primary;
    }
  }
}
</style>
