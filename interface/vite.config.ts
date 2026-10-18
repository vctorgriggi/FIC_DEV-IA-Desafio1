import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Em desenvolvimento (npm run dev), a API Python roda à parte: python -m src.main interface.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
  build: { outDir: "dist", emptyOutDir: true },
});
