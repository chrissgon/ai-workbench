<script setup lang="ts">
import { useCatalog } from "~/stores/catalog";
const s = useCatalog();
</script>
<template><div>{{ s.items.length }}</div></template>
