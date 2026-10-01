<script setup lang="ts">
import ProductCard from "~/components/ProductCard.vue";
import { useCatalog } from "~/stores/catalog";
const s = useCatalog();
s.load();
</script>
<template><ProductCard v-for="p in s.items" :key="p.id" :product="p" /></template>
