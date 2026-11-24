import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The development launcher starts the API on port 8000; /api is proxied to it.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://localhost:8000" } },
});
