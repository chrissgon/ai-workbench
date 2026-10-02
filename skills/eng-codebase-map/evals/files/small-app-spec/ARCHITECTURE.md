# Architecture: small-app

A single-page storefront that lists the products of a catalog.

## Stack

- Vue 3 with Vite as the build tool.
- Vue Router for navigation; the only route is `/`, served by `src/pages/Home.vue`.
- State is managed with Vuex. The single store is `src/store/index.ts`.

## Components

- `src/main.ts` creates the application and installs the router and the store.
- `src/App.vue` is the root component. It renders the product list: one `ProductCard` per product.
- `src/pages/Home.vue` is the landing page. It requests the products when it is created.
- `src/components/ProductCard.vue` shows the name of one product.

## Data flow

1. `src/pages/Home.vue` requests `/products` from the API with axios.
2. The response is committed to the store.
3. The product list is rendered from the store.

## Configuration

- `VITE_API_URL`: base URL of the catalog API.
