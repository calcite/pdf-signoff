<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { getSession, getSignatureAspect, savePlacements } from "./api";
import PdfDocument from "./components/PdfDocument.vue";
import SignatureContextMenu from "./components/SignatureContextMenu.vue";
import {
    addPlacement,
    aspectMismatchedPlacementPages,
    initializePlacements,
    isPlacementStateValid,
    movePlacement,
    removePlacement,
    removeSelectedPlacement,
    resizePlacement,
    selectPlacement,
    serializedPlacements,
    type NormalizedPoint,
    type PageSize,
    type PlacementState,
} from "./placement";

interface ContextMenuState {
    id: number;
    x: number;
    y: number;
}

const state = ref<PlacementState>(initializePlacements([]));
const pageCount = ref(0);
const placementWidth = ref(0);
const imageAspect = ref(0);
const pageSizes = ref(new Map<number, PageSize>());
const ready = ref(false);
const placeMode = ref(false);
const saving = ref(false);
const saved = ref(false);
const errorMessage = ref("");
const contextMenu = ref<ContextMenuState | null>(null);

const canSave = computed(
    () =>
        ready.value &&
        !saving.value &&
        !saved.value &&
        isPlacementStateValid(
            state.value,
            pageCount.value,
            pageSizes.value,
            imageAspect.value,
        ),
);

const saveDisabledReason = computed(() => {
    if (errorMessage.value || saving.value || saved.value) {
        return "";
    }
    if (!ready.value) {
        return "Loading review session.";
    }
    if (state.value.placements.length === 0) {
        return "Add a signature to enable Save.";
    }
    if (pageSizes.value.size < pageCount.value) {
        return "Loading page measurements before Save can be enabled.";
    }
    const affectedPages = aspectMismatchedPlacementPages(
        state.value,
        pageSizes.value,
        imageAspect.value,
    );
    if (affectedPages.length > 0) {
        const pages = affectedPages.map((page) => `page ${page}`).join(", ");
        return `Signatures on ${pages} do not match the current image shape. Resize or remove them to enable Save.`;
    }
    return canSave.value ? "" : "Correct or remove invalid signatures to enable Save.";
});

function reportSessionError(_error: unknown): void {
    errorMessage.value = "Unable to load the review session.";
}

function reportDocumentError(source: "document" | "page", _error: unknown): void {
    errorMessage.value =
        source === "document"
            ? "Unable to load the PDF document."
            : "Unable to render a PDF page.";
}

function onPageReady(page: number, size: PageSize): void {
    pageSizes.value = new Map(pageSizes.value).set(page, size);
}

function onPageClick(page: number, point: NormalizedPoint, size: PageSize): void {
    if (!placeMode.value) {
        return;
    }
    state.value = addPlacement(
        state.value,
        page,
        point,
        placementWidth.value,
        size,
        imageAspect.value,
    );
    placeMode.value = false;
    saved.value = false;
}

function onMove(id: number, x: number, y: number): void {
    state.value = movePlacement(state.value, id, x, y);
    saved.value = false;
}

function onResize(id: number, width: number, page: PageSize): void {
    state.value = resizePlacement(state.value, id, width, page, imageAspect.value);
    const placement = state.value.placements.find((candidate) => candidate.id === id);
    if (placement !== undefined) {
        placementWidth.value = placement.width;
    }
    saved.value = false;
}

function onSelect(id: number | null): void {
    state.value = selectPlacement(state.value, id);
    contextMenu.value = null;
}

function openContextMenu(id: number, clientX: number, clientY: number): void {
    state.value = selectPlacement(state.value, id);
    contextMenu.value = {
        id,
        x: Math.max(8, Math.min(clientX, window.innerWidth - 184)),
        y: Math.max(8, Math.min(clientY, window.innerHeight - 56)),
    };
}

function removeFromContextMenu(): void {
    if (contextMenu.value === null) {
        return;
    }
    state.value = removePlacement(state.value, contextMenu.value.id);
    contextMenu.value = null;
    saved.value = false;
}

function onKeyDown(event: KeyboardEvent): void {
    if (event.key === "Escape") {
        contextMenu.value = null;
        placeMode.value = false;
        return;
    }
    if (event.key === "Delete" && state.value.selectedId !== null) {
        event.preventDefault();
        state.value = removeSelectedPlacement(state.value);
        contextMenu.value = null;
        saved.value = false;
    }
}

async function save(): Promise<void> {
    if (!canSave.value) {
        return;
    }
    saving.value = true;
    errorMessage.value = "";
    try {
        await savePlacements(serializedPlacements(state.value));
        saved.value = true;
        placeMode.value = false;
        contextMenu.value = null;
    } catch (_error) {
        errorMessage.value = "Save failed. Placements were not changed.";
    } finally {
        saving.value = false;
    }
}

onMounted(async () => {
    window.addEventListener("keydown", onKeyDown);
    try {
        const [session, aspect] = await Promise.all([
            getSession(),
            getSignatureAspect(),
        ]);
        pageCount.value = session.pageCount;
        placementWidth.value = session.defaultSignatureWidth;
        imageAspect.value = aspect;
        state.value = initializePlacements(session.initialPlacements);
        ready.value = true;
    } catch (error) {
        reportSessionError(error);
    }
});

onBeforeUnmount(() => {
    window.removeEventListener("keydown", onKeyDown);
});
</script>

<template>
    <div class="app-shell">
        <header class="toolbar" aria-label="Document actions">
            <button
                type="button"
                class="place-button"
                :class="{ active: placeMode }"
                :disabled="!ready || saving || saved"
                :aria-pressed="placeMode"
                @click="placeMode = !placeMode"
            >
                Place signature
            </button>
            <p class="status" aria-live="polite">
                <span v-if="errorMessage" class="error">{{ errorMessage }}</span>
                <span v-else-if="saved" class="saved">Saved</span>
                <span v-else-if="saving">Saving</span>
                <span v-else-if="saveDisabledReason" class="error">{{ saveDisabledReason }}</span>
                <span v-else-if="placeMode">Click a page to place</span>
            </p>
            <button type="button" class="save-button" :disabled="!canSave" @click="save">
                Save
            </button>
        </header>

        <PdfDocument
            v-if="ready"
            :image-aspect="imageAspect"
            :page-count="pageCount"
            :place-mode="placeMode"
            :placement-width="placementWidth"
            :placements="state.placements"
            :selected-id="state.selectedId"
            @context="openContextMenu"
            @error="reportDocumentError"
            @move="onMove"
            @page-click="onPageClick"
            @page-ready="onPageReady"
            @resize="onResize"
            @select="onSelect"
        />
        <main v-else class="document">
            <div class="loading-page" aria-label="Loading review session" />
        </main>

        <SignatureContextMenu
            v-if="contextMenu"
            :x="contextMenu.x"
            :y="contextMenu.y"
            @close="contextMenu = null"
            @remove="removeFromContextMenu"
        />
    </div>
</template>
