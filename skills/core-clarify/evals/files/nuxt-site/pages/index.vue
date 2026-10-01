<script setup lang="ts">
const { data: plans } = await useFetch("/api/plans");
</script>

<template>
  <main>
    <h1>Harbor</h1>
    <ul>
      <li v-for="plan in plans" :key="plan.id">{{ plan.name }}</li>
    </ul>
  </main>
</template>
