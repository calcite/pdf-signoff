<script setup lang="ts">
import {
    GlobalWorkerOptions,
    getDocument,
    type PDFDocumentProxy,
} from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { onBeforeUnmount, onMounted, shallowRef } from "vue";

import type { EditablePlacement, NormalizedPoint, PageSize } from "../placement";
import PdfPage from "./PdfPage.vue";

GlobalWorkerOptions.workerSrc = workerUrl;

const props = defineProps<{
    imageAspect: number;
    pageCount: number;
    placeMode: boolean;
    placementWidth: number;
    placements: EditablePlacement[];
    selectedId: number | null;
}>();

const emit = defineEmits<{
    context: [id: number, clientX: number, clientY: number];
    error: [error: unknown];
    move: [id: number, x: number, y: number];
    pageClick: [page: number, point: NormalizedPoint, size: PageSize];
    pageReady: [page: number, size: PageSize];
    resize: [id: number, width: number, page: PageSize];
    select: [id: number | null];
}>();

const pdf = shallowRef<PDFDocumentProxy | null>(null);
const loadingTask = getDocument({ url: "/api/document", withCredentials: true });

onMounted(async () => {
    try {
        const document = await loadingTask.promise;
        if (document.numPages !== props.pageCount) {
            await document.destroy();
            throw new Error("Document page count does not match the review session");
        }
        pdf.value = document;
    } catch (error) {
        emit("error", error);
    }
});

onBeforeUnmount(() => {
    void loadingTask.destroy();
});
</script>

<template>
    <main class="document" aria-label="PDF document">
        <template v-if="pdf">
            <PdfPage
                v-for="page in pageCount"
                :key="page"
                :document="pdf"
                :image-aspect="imageAspect"
                :page-number="page"
                :place-mode="placeMode"
                :placement-width="placementWidth"
                :placements="placements"
                :selected-id="selectedId"
                @context="(...args) => emit('context', ...args)"
                @error="(error) => emit('error', error)"
                @move="(...args) => emit('move', ...args)"
                @page-click="(...args) => emit('pageClick', ...args)"
                @page-ready="(...args) => emit('pageReady', ...args)"
                @resize="(...args) => emit('resize', ...args)"
                @select="(id) => emit('select', id)"
            />
        </template>
        <div v-else class="loading-page" aria-label="Loading document" />
    </main>
</template>
