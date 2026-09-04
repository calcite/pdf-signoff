// @vitest-environment happy-dom

import type { PDFDocumentProxy, PDFPageProxy, RenderTask } from "pdfjs-dist";
import { createApp, nextTick, type App as VueApp } from "vue";
import { afterEach, describe, expect, it, vi } from "vitest";

import PdfPage from "./PdfPage.vue";

let app: VueApp<Element> | null = null;

async function flush(): Promise<void> {
    await Promise.resolve();
    await Promise.resolve();
    await nextTick();
}

afterEach(() => {
    app?.unmount();
    app = null;
    document.body.replaceChildren();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
});

describe("PDF page rendering", () => {
    it("renders a high-DPI canvas inside the page and positions normalized overlays", async () => {
        vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(600);
        vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
            {} as CanvasRenderingContext2D,
        );
        vi.stubGlobal(
            "requestAnimationFrame",
            (callback: FrameRequestCallback): number => {
                callback(0);
                return 1;
            },
        );
        vi.stubGlobal("cancelAnimationFrame", vi.fn());

        const renderTask = {
            cancel: vi.fn(),
            promise: Promise.resolve(),
        } as unknown as RenderTask;
        const render = vi.fn().mockReturnValue(renderTask);
        const cleanup = vi.fn();
        const pdfPage = {
            cleanup,
            getViewport: ({ scale }: { scale: number }) => ({
                width: 600 * scale,
                height: 800 * scale,
            }),
            render,
        } as unknown as PDFPageProxy;
        const getPage = vi.fn().mockResolvedValue(pdfPage);
        const documentProxy = { getPage } as unknown as PDFDocumentProxy;
        const pageReady = vi.fn();
        const host = document.createElement("div");
        document.body.append(host);

        app = createApp(PdfPage, {
            document: documentProxy,
            imageAspect: 4,
            pageNumber: 1,
            placeMode: false,
            placements: [
                { id: 1, page: 1, x: 0.1, y: 0.2, width: 0.4, height: 0.075 },
            ],
            selectedId: 1,
            onPageReady: pageReady,
        });
        app.mount(host);
        await flush();

        expect(getPage).toHaveBeenCalledWith(1);
        expect(pageReady).toHaveBeenCalledWith(1, { width: 600, height: 800 });
        expect(render).toHaveBeenCalledOnce();
        expect(document.querySelector(".pdf-page > .pdf-canvas")).not.toBeNull();
        const overlay = document.querySelector<HTMLElement>(".signature-overlay");
        expect(overlay?.style.left).toBe("10%");
        expect(overlay?.style.top).toBe("20%");
        expect(overlay?.style.width).toBe("40%");
        expect(overlay?.style.height).toBe("7.5%");
    });
});
