<script setup lang="ts">
import type {
    PDFDocumentProxy,
    PDFPageProxy,
    RenderTask,
} from "pdfjs-dist";
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

import {
    centeredPlacement,
    type EditablePlacement,
    type NormalizedPoint,
    type PageSize,
    type Placement,
} from "../placement";
import SignatureOverlay from "./SignatureOverlay.vue";

const props = defineProps<{
    document: PDFDocumentProxy;
    imageAspect: number;
    pageNumber: number;
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

const container = ref<HTMLElement | null>(null);
const canvas = ref<HTMLCanvasElement | null>(null);
const pageSize = ref<PageSize | null>(null);
const preview = ref<Placement | null>(null);
const signatureUrl = "/api/signature";
const pagePlacements = computed(() =>
    props.placements.filter((placement) => placement.page === props.pageNumber),
);

let pdfPage: PDFPageProxy | null = null;
let renderTask: RenderTask | null = null;
let resizeObserver: ResizeObserver | null = null;
let renderFrame: number | null = null;

function scheduleRender(): void {
    if (renderFrame !== null) {
        cancelAnimationFrame(renderFrame);
    }
    renderFrame = requestAnimationFrame(() => {
        renderFrame = null;
        void renderCanvas();
    });
}

async function renderCanvas(): Promise<void> {
    if (pdfPage === null || container.value === null || canvas.value === null) {
        return;
    }
    const baseViewport = pdfPage.getViewport({ scale: 1 });
    const cssWidth = container.value.clientWidth;
    if (cssWidth <= 0) {
        return;
    }
    const outputScale = Math.min(window.devicePixelRatio || 1, 2);
    const viewport = pdfPage.getViewport({
        scale: (cssWidth / baseViewport.width) * outputScale,
    });
    const context = canvas.value.getContext("2d", { alpha: false });
    if (context === null) {
        throw new Error("Canvas rendering is unavailable");
    }
    renderTask?.cancel();
    canvas.value.width = Math.ceil(viewport.width);
    canvas.value.height = Math.ceil(viewport.height);
    try {
        renderTask = pdfPage.render({ canvas: canvas.value, canvasContext: context, viewport });
        await renderTask.promise;
    } catch (error) {
        if (error instanceof Error && error.name === "RenderingCancelledException") {
            return;
        }
        emit("error", error);
    }
}

function onPageClick(event: MouseEvent): void {
    if (container.value === null || pageSize.value === null) {
        return;
    }
    if (!props.placeMode) {
        emit("select", null);
        return;
    }
    const point = normalizedPoint(event);
    preview.value = null;
    emit(
        "pageClick",
        props.pageNumber,
        point,
        pageSize.value,
    );
}

function normalizedPoint(event: MouseEvent | PointerEvent): NormalizedPoint {
    if (container.value === null) {
        return { x: 0, y: 0 };
    }
    const rect = container.value.getBoundingClientRect();
    return {
        x: (event.clientX - rect.left) / rect.width,
        y: (event.clientY - rect.top) / rect.height,
    };
}

function updatePreview(event: PointerEvent): void {
    if (event.pointerType === "touch" || pageSize.value === null || !props.placeMode) {
        return;
    }
    preview.value = centeredPlacement(
        props.pageNumber,
        normalizedPoint(event),
        props.placementWidth,
        pageSize.value,
        props.imageAspect,
    );
}

function clearPreview(): void {
    preview.value = null;
}

watch(
    () => props.placeMode,
    (enabled) => {
        if (!enabled) {
            clearPreview();
        }
    },
);

onMounted(async () => {
    try {
        pdfPage = await props.document.getPage(props.pageNumber);
        const viewport = pdfPage.getViewport({ scale: 1 });
        pageSize.value = { width: viewport.width, height: viewport.height };
        emit("pageReady", props.pageNumber, pageSize.value);
        resizeObserver = new ResizeObserver(scheduleRender);
        if (container.value !== null) {
            resizeObserver.observe(container.value);
        }
        scheduleRender();
    } catch (error) {
        emit("error", error);
    }
});

onBeforeUnmount(() => {
    resizeObserver?.disconnect();
    renderTask?.cancel();
    if (renderFrame !== null) {
        cancelAnimationFrame(renderFrame);
    }
    pdfPage?.cleanup();
});
</script>

<template>
    <section class="page-shell" :aria-label="`Page ${pageNumber}`">
        <div class="page-number">{{ String(pageNumber).padStart(2, "0") }}</div>
        <div
            ref="container"
            class="pdf-page"
            :class="{ 'place-mode': placeMode }"
            :style="{
                aspectRatio: pageSize ? `${pageSize.width} / ${pageSize.height}` : undefined,
            }"
            @click="onPageClick"
            @pointerleave="clearPreview"
            @pointermove="updatePreview"
        >
            <canvas ref="canvas" class="pdf-canvas" />
            <div
                v-if="preview"
                class="signature-preview"
                :style="{
                    left: `${preview.x * 100}%`,
                    top: `${preview.y * 100}%`,
                    width: `${preview.width * 100}%`,
                    height: `${preview.height * 100}%`,
                }"
                aria-hidden="true"
            >
                <img :src="signatureUrl" alt="" draggable="false" />
            </div>
            <SignatureOverlay
                v-for="placement in pagePlacements"
                :key="placement.id"
                :placement="placement"
                :selected="placement.id === selectedId"
                :page-size="pageSize ?? { width: 1, height: 1 }"
                :image-aspect="imageAspect"
                @context="(...args) => emit('context', ...args)"
                @move="(...args) => emit('move', ...args)"
                @resize="(id, width) => pageSize && emit('resize', id, width, pageSize)"
                @select="(id) => emit('select', id)"
            />
        </div>
    </section>
</template>
