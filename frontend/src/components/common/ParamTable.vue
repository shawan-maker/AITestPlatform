<template>
  <div class="ui-param-table-wrap">
    <table class="ui-param-table">
      <thead>
        <tr>
          <slot name="head" />
        </tr>
      </thead>
      <tbody>
        <slot />
      </tbody>
    </table>
    <button
      v-if="canAdd"
      type="button"
      class="ui-add-param-bar"
      @click="$emit('add')"
    >
      + {{ addLabel }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  canAdd: { type: Boolean, default: true },
  addLabel: { type: String, default: '' },
})

defineEmits(['add'])
</script>
