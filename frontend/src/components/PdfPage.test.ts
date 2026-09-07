// @vitest-environment happy-dom

import type { PDFDocumentProxy, PDFPageProxy, RenderTask } from "pdfjs-dist";
import { createApp, nextTick, type App as VueApp } from "vue";
import { afterEach, describe, expect, it, vi } from "vitest";

import PdfPage from "./PdfPage.vue";

let app: VueApp<Element> | null = null;
let intersectionObserver: MockIntersectionObserver | null = null;

class MockIntersectionObserver {
    readonly observed: Element[] = [];

    constructor(
        private readonly callback: IntersectionObserverCallback,
    ) {
        intersectionObserver = this;
    }

    disconnect(): void {}

    observe(target: Element): void {
        this.observed.push(target);
    }

    unobserve(): void {}

    setVisible(isIntersecting: boolean): void {
        const target = this.observed[0];
        if (target === undefined) {
            throw new Error("No observed page");
        }
        this.callback(
            [{ isIntersecting, target } as IntersectionObserverEntry],
            this as unknown as IntersectionObserver,
        );
    }

    takeRecords(): IntersectionObserverEntry[] {
        return [];
    }
}

async function flush(): Promise<void> {
    await Promise.resolve();
    await Promise.resolve();
    await nextTick();
}

afterEach(() => {
    app?.unmount();
    app = null;
    intersectionObserver = null;
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
        vi.stubGlobal("IntersectionObserver", undefined);

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
        const host = document.createElement("div");
        document.body.append(host);

        app = createApp(PdfPage, {
            document: documentProxy,
            imageAspect: 4,
            pageNumber: 1,
            pageSize: { width: 600, height: 800 },
            placeMode: false,
            placementWidth: 0.4,
            placements: [
                { id: 1, page: 1, x: 0.1, y: 0.2, width: 0.4, height: 0.075 },
            ],
            selectedId: 1,
        });
        app.mount(host);
        await flush();

        expect(getPage).toHaveBeenCalledWith(1);
        expect(render).toHaveBeenCalledOnce();
        expect(document.querySelector(".pdf-page > .pdf-canvas")).not.toBeNull();
        const overlay = document.querySelector<HTMLElement>(".signature-overlay");
        expect(overlay?.style.left).toBe("10%");
        expect(overlay?.style.top).toBe("20%");
        expect(overlay?.style.width).toBe("40%");
        expect(overlay?.style.height).toBe("7.5%");
    });

    it("previews the same edge-clamped signature that a click will place", async () => {
        vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(600);
        vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
            bottom: 800,
            height: 800,
            left: 0,
            right: 600,
            top: 0,
            width: 600,
        } as DOMRect);
        vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
            {} as CanvasRenderingContext2D,
        );
        vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback): number => {
            callback(0);
            return 1;
        });
        vi.stubGlobal("cancelAnimationFrame", vi.fn());

        const pdfPage = {
            cleanup: vi.fn(),
            getViewport: ({ scale }: { scale: number }) => ({
                width: 600 * scale,
                height: 800 * scale,
            }),
            render: vi.fn().mockReturnValue({ cancel: vi.fn(), promise: Promise.resolve() }),
        } as unknown as PDFPageProxy;
        const host = document.createElement("div");
        document.body.append(host);
        app = createApp(PdfPage, {
            document: { getPage: vi.fn().mockResolvedValue(pdfPage) } as unknown as PDFDocumentProxy,
            imageAspect: 4,
            pageNumber: 1,
            pageSize: { width: 600, height: 800 },
            placeMode: true,
            placementWidth: 0.4,
            placements: [],
            selectedId: null,
        });
        app.mount(host);
        await flush();

        document.querySelector<HTMLElement>(".pdf-page")?.dispatchEvent(
            new MouseEvent("pointermove", { bubbles: true, clientX: 590, clientY: 10 }),
        );
        await flush();

        const preview = document.querySelector<HTMLElement>(".signature-preview");
        expect(preview?.style.left).toBe("60%");
        expect(preview?.style.top).toBe("0%");
        expect(preview?.style.width).toBe("40%");
        expect(Number.parseFloat(preview?.style.height ?? "")).toBeCloseTo(7.5);
    });

    it("rasterises a page only when it is near the viewport", async () => {
        vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(600);
        vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
            {} as CanvasRenderingContext2D,
        );
        vi.stubGlobal("IntersectionObserver", MockIntersectionObserver);
        vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback): number => {
            callback(0);
            return 1;
        });
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
        const host = document.createElement("div");
        document.body.append(host);

        app = createApp(PdfPage, {
            document: { getPage } as unknown as PDFDocumentProxy,
            imageAspect: 4,
            pageNumber: 1,
            pageSize: { width: 600, height: 800 },
            placeMode: false,
            placementWidth: 0.4,
            placements: [],
            selectedId: null,
        });
        app.mount(host);
        await flush();

        expect(getPage).not.toHaveBeenCalled();
        expect(render).not.toHaveBeenCalled();

        intersectionObserver?.setVisible(true);
        await flush();

        expect(render).toHaveBeenCalledOnce();
        expect(document.querySelector<HTMLCanvasElement>(".pdf-canvas")?.width).toBe(600);

        intersectionObserver?.setVisible(false);
        await flush();

        expect(renderTask.cancel).toHaveBeenCalledOnce();
        expect(cleanup).toHaveBeenCalledOnce();
        expect(document.querySelector<HTMLCanvasElement>(".pdf-canvas")?.width).toBe(0);
    });
});
