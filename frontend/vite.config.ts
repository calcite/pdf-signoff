import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
    plugins: [vue()],
    build: {
        outDir: "../pdf_signoff/web_dist",
        emptyOutDir: true,
    },
    server: {
        proxy: {
            "/api": "http://127.0.0.1:8000",
        },
    },
});
