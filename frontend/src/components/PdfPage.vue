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
    pageSize: PageSize;
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
    resize: [id: number, width: number, page: PageSize];
    select: [id: number | null];
}>();

const container = ref<HTMLElement | null>(null);
const canvas = ref<HTMLCanvasElement | null>(null);
const preview = ref<Placement | null>(null);
const signatureUrl = "/api/signature";
const pagePlacements = computed(() =>
    props.placements.filter((placement) => placement.page === props.pageNumber),
);

let pdfPage: PDFPageProxy | null = null;
let renderTask: RenderTask | null = null;
let resizeObserver: ResizeObserver | null = null;
let intersectionObserver: IntersectionObserver | null = null;
let renderFrame: number | null = null;
let pageLoading: Promise<PDFPageProxy> | null = null;
let isVisible = false;

function scheduleRender(): void {
    if (!isVisible) {
        return;
    }
    if (renderFrame !== null) {
        cancelAnimationFrame(renderFrame);
    }
    renderFrame = requestAnimationFrame(() => {
        renderFrame = null;
        void renderCanvas();
    });
}

async function renderCanvas(): Promise<void> {
    if (!isVisible || pdfPage === null || container.value === null || canvas.value === null) {
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
    if (container.value === null) {
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
        props.pageSize,
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
    if (event.pointerType === "touch" || !props.placeMode) {
        return;
    }
    preview.value = centeredPlacement(
        props.pageNumber,
        normalizedPoint(event),
        props.placementWidth,
        props.pageSize,
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

async function loadAndRender(): Promise<void> {
    if (pdfPage === null) {
        pageLoading ??= props.document.getPage(props.pageNumber);
        try {
            const loadedPage = await pageLoading;
            if (!isVisible) {
                loadedPage.cleanup();
                return;
            }
            pdfPage = loadedPage;
        } catch (error) {
            emit("error", error);
            return;
        } finally {
            pageLoading = null;
        }
    }
    scheduleRender();
}

function unloadPage(): void {
    renderTask?.cancel();
    renderTask = null;
    if (renderFrame !== null) {
        cancelAnimationFrame(renderFrame);
        renderFrame = null;
    }
    if (canvas.value !== null) {
        canvas.value.width = 0;
        canvas.value.height = 0;
    }
    pdfPage?.cleanup();
    pdfPage = null;
}

function updateVisibility(entries: IntersectionObserverEntry[]): void {
    const entry = entries.find((candidate) => candidate.target === container.value);
    if (entry === undefined) {
        return;
    }
    isVisible = entry.isIntersecting;
    if (isVisible) {
        void loadAndRender();
    } else {
        unloadPage();
    }
}

onMounted(() => {
    resizeObserver = new ResizeObserver(scheduleRender);
    if (container.value !== null) {
        resizeObserver.observe(container.value);
    }
    if (typeof IntersectionObserver === "undefined") {
        isVisible = true;
        void loadAndRender();
        return;
    }
    intersectionObserver = new IntersectionObserver(updateVisibility, {
        rootMargin: "600px 0px",
    });
    if (container.value !== null) {
        intersectionObserver.observe(container.value);
    }
});

onBeforeUnmount(() => {
    isVisible = false;
    intersectionObserver?.disconnect();
    resizeObserver?.disconnect();
    unloadPage();
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
                aspectRatio: `${pageSize.width} / ${pageSize.height}`,
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
                :page-size="pageSize"
                :image-aspect="imageAspect"
                @context="(...args) => emit('context', ...args)"
                @move="(...args) => emit('move', ...args)"
                @resize="(id, width) => emit('resize', id, width, pageSize)"
                @select="(id) => emit('select', id)"
            />
        </div>
    </section>
</template>
