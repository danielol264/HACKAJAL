import { defineConfig } from 'vite';

// Lee el .env único de la raíz del proyecto (solo expone las variables VITE_*)
export default defineConfig({
  envDir: '..',
});
