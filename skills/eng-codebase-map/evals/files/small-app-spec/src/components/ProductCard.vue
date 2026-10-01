<script setup lang="ts">
defineProps<{ product: { id: string; name: string } }>();
</script>
<template><article class="card">{{ product.name }}</article></template>
