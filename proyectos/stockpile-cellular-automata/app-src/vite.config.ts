import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * Las señales transformadas se copian como un JSON público y los cuadros se
 * construyen en el navegador. No se distribuyen binarios ni tags privados.
 */
export default defineConfig({
  plugins: [react()],
  base: "./",
  build: {
    outDir: "../app",
    emptyOutDir: true,
    assetsInlineLimit: 0,
    copyPublicDir: true,
  },
  server: { open: true },
});
