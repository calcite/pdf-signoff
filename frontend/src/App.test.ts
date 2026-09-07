// @vitest-environment happy-dom

import { createApp, defineComponent, h, nextTick, type App as VueApp } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({
    getSession: vi.fn(),
    getSignatureAspect: vi.fn(),
    savePlacements: vi.fn(),
}));

vi.mock("./api", () => api);

vi.mock("./components/PdfDocument.vue", () => ({
    default: defineComponent({
        name: "PdfDocument",
        props: {
            placeMode: Boolean,
            placements: { type: Array, required: true },
        },
        emits: ["context", "pageClick", "pageReady", "resize", "select"],
        setup(props, { emit }) {
            const page = { width: 600, height: 800 };
            return () =>
                h(
                    "div",
                    {
                        "data-count": String(props.placements.length),
                        "data-place-mode": String(props.placeMode),
                        "data-testid": "pdf-document",
                    },
                    [
                        h("button", {
                            "data-testid": "page-ready",
                            onClick: () => emit("pageReady", 1, page),
                        }),
                        h("button", {
                            "data-testid": "page-click",
                            onClick: () => emit("pageClick", 1, { x: 0.99, y: 0.01 }, page),
                        }),
                        h("button", {
                            "data-testid": "select-first",
                            onClick: () => emit("select", 1),
                        }),
                        h("button", {
                            "data-testid": "context-second",
                            onClick: () => emit("context", 2, 20, 20),
                        }),
                        h("button", {
                            "data-testid": "resize-first",
                            onClick: () => emit("resize", 1, 0.25, page),
                        }),
                    ],
                );
        },
    }),
}));

import App from "./App.vue";

let app: VueApp<Element> | null = null;
let host: HTMLElement;

async function flush(): Promise<void> {
    await Promise.resolve();
    await Promise.resolve();
    await nextTick();
}

function element(selector: string): HTMLElement {
    const found = document.querySelector<HTMLElement>(selector);
    if (found === null) {
        throw new Error(`Missing test element: ${selector}`);
    }
    return found;
}

async function click(selector: string): Promise<void> {
    element(selector).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    await flush();
}

async function mountApp(): Promise<void> {
    host = document.createElement("div");
    document.body.append(host);
    app = createApp(App);
    app.mount(host);
    await flush();
}

beforeEach(() => {
    api.getSignatureAspect.mockResolvedValue(4);
    api.savePlacements.mockResolvedValue(undefined);
});

afterEach(() => {
    app?.unmount();
    app = null;
    document.body.replaceChildren();
    vi.clearAllMocks();
});

describe("review interface contract", () => {
    it("uses a one-shot placement mode and sends only the normalized placements", async () => {
        api.getSession.mockResolvedValue({
            pageCount: 1,
            initialPlacements: [],
            defaultSignatureWidth: 0.4,
        });
        await mountApp();
        await click('[data-testid="page-ready"]');

        const toolbarButtons = [...document.querySelectorAll(".toolbar button")];
        expect(toolbarButtons.map((button) => button.textContent?.trim())).toEqual([
            "Place signature",
            "Save",
        ]);
        expect(element(".save-button")).toHaveProperty("disabled", true);
        expect(element(".status").textContent).toContain("Add a signature to enable Save.");

        await click(".place-button");
        expect(element('[data-testid="pdf-document"]').dataset.placeMode).toBe("true");
        await click('[data-testid="page-click"]');
        expect(element('[data-testid="pdf-document"]').dataset.placeMode).toBe("false");
        expect(element('[data-testid="pdf-document"]').dataset.count).toBe("1");
        expect(element(".save-button")).toHaveProperty("disabled", false);

        await click(".save-button");
        expect(api.savePlacements).toHaveBeenCalledWith([
            {
                page: 1,
                x: 0.6,
                y: 0,
                width: 0.4,
                height: 0.07500000000000001,
            },
        ]);
        expect(document.querySelector(".saved")?.textContent).toBe("Saved");
    });

    it("preloads one collection and removes selected items by Delete or custom menu", async () => {
        api.getSession.mockResolvedValue({
            pageCount: 1,
            initialPlacements: [
                { page: 1, x: 0.1, y: 0.2, width: 0.4, height: 0.075 },
                { page: 1, x: 0.2, y: 0.4, width: 0.4, height: 0.075 },
            ],
            defaultSignatureWidth: 0.4,
        });
        await mountApp();
        await click('[data-testid="page-ready"]');
        expect(element('[data-testid="pdf-document"]').dataset.count).toBe("2");

        await click('[data-testid="select-first"]');
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "Delete" }));
        await flush();
        expect(element('[data-testid="pdf-document"]').dataset.count).toBe("1");

        await click('[data-testid="context-second"]');
        const menuCommands = [...document.querySelectorAll(".signature-menu button")];
        expect(menuCommands).toHaveLength(1);
        expect(menuCommands[0].textContent?.trim()).toBe("Remove signature");
        menuCommands[0].dispatchEvent(new MouseEvent("click", { bubbles: true }));
        await flush();
        expect(element('[data-testid="pdf-document"]').dataset.count).toBe("0");
        expect(element(".save-button")).toHaveProperty("disabled", true);
    });

    it("explains how to correct preloaded signatures that mismatch the current image", async () => {
        api.getSession.mockResolvedValue({
            pageCount: 1,
            initialPlacements: [
                { page: 1, x: 0.1, y: 0.2, width: 0.4, height: 0.2 },
            ],
            defaultSignatureWidth: 0.4,
        });
        await mountApp();
        await click('[data-testid="page-ready"]');

        expect(element(".save-button")).toHaveProperty("disabled", true);
        expect(element(".status").textContent).toContain("Signatures on page 1");
        expect(element(".status").textContent).toContain("Resize or remove them to enable Save.");

        await click('[data-testid="resize-first"]');

        expect(element(".save-button")).toHaveProperty("disabled", false);
    });

    it("uses the clamped width from a resize for later placements", async () => {
        api.getSession.mockResolvedValue({
            pageCount: 1,
            initialPlacements: [
                { page: 1, x: 0.1, y: 0.2, width: 0.4, height: 0.075 },
            ],
            defaultSignatureWidth: 0.4,
        });
        await mountApp();
        await click('[data-testid="page-ready"]');
        await click('[data-testid="resize-first"]');
        await click(".place-button");
        await click('[data-testid="page-click"]');
        await click(".save-button");

        expect(api.savePlacements).toHaveBeenCalledWith([
            { page: 1, x: 0.1, y: 0.2, width: 0.25, height: 0.046875 },
            { page: 1, x: 0.75, y: 0, width: 0.25, height: 0.046875 },
        ]);
    });
});
