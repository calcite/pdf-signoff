<script setup lang="ts">
import { onBeforeUnmount } from "vue";

import {
    desiredResizeWidth,
    type EditablePlacement,
    type NormalizedPoint,
    type PageSize,
} from "../placement";

const props = defineProps<{
    placement: EditablePlacement;
    selected: boolean;
    pageSize: PageSize;
    imageAspect: number;
}>();

const emit = defineEmits<{
    context: [id: number, clientX: number, clientY: number];
    move: [id: number, x: number, y: number];
    resize: [id: number, width: number];
    select: [id: number];
}>();

const signatureUrl = "/api/signature";

let startPointer: NormalizedPoint | null = null;
let startPlacement: EditablePlacement | null = null;
let pageRect: DOMRect | null = null;
let mode: "move" | "resize" = "move";
let longPressTimer: number | undefined;
let pointerId: number | null = null;

function normalizedPointer(event: PointerEvent): NormalizedPoint {
    if (pageRect === null) {
        return { x: 0, y: 0 };
    }
    return {
        x: (event.clientX - pageRect.left) / pageRect.width,
        y: (event.clientY - pageRect.top) / pageRect.height,
    };
}

function clearLongPress(): void {
    window.clearTimeout(longPressTimer);
    longPressTimer = undefined;
}

function stopInteraction(): void {
    clearLongPress();
    startPointer = null;
    startPlacement = null;
    pageRect = null;
    pointerId = null;
    window.removeEventListener("pointermove", onPointerMove);
    window.removeEventListener("pointerup", stopInteraction);
    window.removeEventListener("pointercancel", stopInteraction);
}

function onPointerMove(event: PointerEvent): void {
    if (
        pointerId !== event.pointerId ||
        startPointer === null ||
        startPlacement === null
    ) {
        return;
    }
    const current = normalizedPointer(event);
    if (
        Math.abs(current.x - startPointer.x) > 0.008 ||
        Math.abs(current.y - startPointer.y) > 0.008
    ) {
        clearLongPress();
    }
    if (mode === "move") {
        emit(
            "move",
            props.placement.id,
            startPlacement.x + current.x - startPointer.x,
            startPlacement.y + current.y - startPointer.y,
        );
    } else {
        emit(
            "resize",
            props.placement.id,
            desiredResizeWidth(
                startPlacement,
                startPointer,
                current,
                props.pageSize,
                props.imageAspect,
            ),
        );
    }
}

function onPointerDown(event: PointerEvent): void {
    if (event.button !== 0) {
        return;
    }
    event.preventDefault();
    event.stopPropagation();
    emit("select", props.placement.id);
    const parent = (event.currentTarget as HTMLElement).parentElement;
    if (parent === null) {
        return;
    }
    pointerId = event.pointerId;
    pageRect = parent.getBoundingClientRect();
    startPointer = normalizedPointer(event);
    startPlacement = { ...props.placement };
    mode = (event.target as HTMLElement).dataset.resize === "true" ? "resize" : "move";
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", stopInteraction);
    window.addEventListener("pointercancel", stopInteraction);

    if (event.pointerType === "touch" && mode === "move") {
        const { clientX, clientY } = event;
        longPressTimer = window.setTimeout(() => {
            emit("context", props.placement.id, clientX, clientY);
            stopInteraction();
        }, 550);
    }
}

function openContextMenu(event: MouseEvent): void {
    emit("select", props.placement.id);
    emit("context", props.placement.id, event.clientX, event.clientY);
}

onBeforeUnmount(stopInteraction);
</script>

<template>
    <div
        class="signature-overlay"
        :class="{ selected }"
        :style="{
            left: `${placement.x * 100}%`,
            top: `${placement.y * 100}%`,
            width: `${placement.width * 100}%`,
            height: `${placement.height * 100}%`,
        }"
        role="img"
        :aria-label="`Signature on page ${placement.page}`"
        @pointerdown="onPointerDown"
        @click.stop
        @contextmenu.prevent.stop="openContextMenu"
    >
        <img :src="signatureUrl" alt="" draggable="false" />
        <span class="resize-handle" data-resize="true" aria-hidden="true" />
    </div>
</template>
