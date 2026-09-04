import type { Placement } from "./placement";

export interface SessionMetadata {
    pageCount: number;
    initialPlacements: Placement[];
    defaultSignatureWidth: number;
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
    const response = await fetch(url, {
        ...init,
        cache: "no-store",
        credentials: "same-origin",
    });
    if (!response.ok) {
        throw new Error(`Request failed (${response.status})`);
    }
    return (await response.json()) as T;
}

export function getSession(): Promise<SessionMetadata> {
    return request<SessionMetadata>("/api/session");
}

export async function getSignatureAspect(): Promise<number> {
    const image = new Image();
    image.src = "/api/signature";
    await image.decode();
    if (image.naturalWidth <= 0 || image.naturalHeight <= 0) {
        throw new Error("Signature image has invalid dimensions");
    }
    return image.naturalWidth / image.naturalHeight;
}

export async function savePlacements(placements: Placement[]): Promise<void> {
    const result = await request<{ ok: boolean }>("/api/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ placements }),
    });
    if (result.ok !== true) {
        throw new Error("Save was not confirmed");
    }
}
