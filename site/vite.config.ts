import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Base configurable : `/credit-process-intelligence/` pour GitHub Pages, `/` en local si besoin.
const base = process.env.BASE_PATH ?? "/credit-process-intelligence/";

export default defineConfig({
  base,
  plugins: [react()],
  build: {
    target: "es2022",
    chunkSizeWarningLimit: 1600,
    rollupOptions: {
      output: {
        manualChunks: {
          echarts: ["echarts"],
          bpmn: ["bpmn-js/lib/NavigatedViewer"],
          flow: ["@xyflow/react", "@dagrejs/dagre"],
        },
      },
    },
  },
  test: {
    include: ["tests/**/*.test.ts"],
    environment: "node",
  },
});
