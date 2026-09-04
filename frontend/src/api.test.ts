import { afterEach, describe, expect, it, vi } from "vitest";

import { savePlacements } from "./api";

afterEach(() => {
    vi.unstubAllGlobals();
});

describe("review API", () => {
    it("saves only the normalized placement collection", async () => {
        const fetch = vi.fn().mockResolvedValue(
            new Response(JSON.stringify({ ok: true }), {
                status: 200,
                headers: { "Content-Type": "application/json" },
            }),
        );
        vi.stubGlobal("fetch", fetch);
        const placements = [
            { page: 1, x: 0.1, y: 0.2, width: 0.4, height: 0.075 },
        ];

        await savePlacements(placements);

        expect(fetch).toHaveBeenCalledWith("/api/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ placements }),
            cache: "no-store",
            credentials: "same-origin",
        });
    });
});
