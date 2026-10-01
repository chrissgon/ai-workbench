import { defineStore } from "pinia";
export const useCatalog = defineStore("catalog", {
  state: () => ({ items: [] as { id: string; name: string }[] }),
  actions: { async load() { const r = await fetch(`${import.meta.env.VITE_API_URL}/products`); this.items = await r.json(); } }
});
