import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    watch: process.platform === "win32" ? {usePolling:true, interval:500} : undefined,
    proxy: {
      "/api": {
        target: process.env.NUTRIFLOW_DEV_API_TARGET ?? "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
