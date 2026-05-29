<template>
  <section class="ui-section-panel">
    <h3 class="ui-section-panel__title">{{ title }}</h3>
    <div class="ui-section-panel__divider" />
    <div class="ui-section-panel__body">
      <slot />
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
})
</script>
