export default defineNuxtConfig({
  ssr: true,
  nitro: {
    preset: "node-server",
  },
  app: {
    head: {
      title: "Harbor",
    },
  },
});
