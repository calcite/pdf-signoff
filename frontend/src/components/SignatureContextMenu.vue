<script setup lang="ts">
import { nextTick, onMounted, ref } from "vue";

defineProps<{
    x: number;
    y: number;
}>();

const emit = defineEmits<{
    close: [];
    remove: [];
}>();

const command = ref<HTMLButtonElement | null>(null);

onMounted(async () => {
    await nextTick();
    command.value?.focus();
});
</script>

<template>
    <Teleport to="body">
        <div class="context-dismiss" @pointerdown.self="emit('close')">
            <div
                class="signature-menu"
                :style="{ left: `${x}px`, top: `${y}px` }"
                role="menu"
                @contextmenu.prevent
            >
                <button ref="command" type="button" role="menuitem" @click="emit('remove')">
                    Remove signature
                </button>
            </div>
        </div>
    </Teleport>
</template>
