import { describe, expect, it } from "vitest";

import {
    addPlacement,
    desiredResizeWidth,
    initializePlacements,
    isPlacementStateValid,
    movePlacement,
    normalizedHeight,
    removePlacement,
    removeSelectedPlacement,
    resizePlacement,
    selectPlacement,
    serializedPlacements,
    type PageSize,
} from "./placement";

const portrait: PageSize = { width: 600, height: 800 };
const imageAspect = 4;

describe("normalized placement geometry", () => {
    it("converts the PNG aspect into displayed page coordinates", () => {
        expect(normalizedHeight(0.4, imageAspect, portrait)).toBeCloseTo(0.075);
    });

    it("adds a centered placement and clamps it to every page edge", () => {
        const state = addPlacement(
            initializePlacements([]),
            2,
            { x: 0.99, y: 0.01 },
            0.4,
            portrait,
            imageAspect,
        );

        expect(state.placements).toEqual([
            {
                id: 1,
                page: 2,
                x: 0.6,
                y: 0,
                width: 0.4,
                height: 0.07500000000000001,
            },
        ]);
        expect(state.selectedId).toBe(1);
    });

    it("scales a signature down when its physical aspect cannot fit the page", () => {
        const state = addPlacement(
            initializePlacements([]),
            1,
            { x: 0.5, y: 0.5 },
            0.8,
            { width: 1000, height: 100 },
            0.5,
        );

        expect(state.placements[0].width).toBeCloseTo(0.05);
        expect(state.placements[0].height).toBeCloseTo(1);
        expect(state.placements[0].y).toBe(0);
    });

    it("clamps movement without changing normalized size", () => {
        const initial = initializePlacements([
            { page: 1, x: 0.2, y: 0.2, width: 0.3, height: 0.1 },
        ]);

        const low = movePlacement(initial, 1, -0.2, -0.4);
        const high = movePlacement(low, 1, 2, 2);

        expect(low.placements[0]).toMatchObject({ x: 0, y: 0, width: 0.3, height: 0.1 });
        expect(high.placements[0]).toMatchObject({ x: 0.7, y: 0.9, width: 0.3, height: 0.1 });
    });

    it("uses the dominant pointer axis and resizes with locked physical aspect", () => {
        const initial = initializePlacements([
            { page: 1, x: 0.7, y: 0.8, width: 0.2, height: 0.0375 },
        ]);
        const desired = desiredResizeWidth(
            initial.placements[0],
            { x: 0.9, y: 0.8375 },
            { x: 0.91, y: 0.9 },
            portrait,
            imageAspect,
        );
        const resized = resizePlacement(initial, 1, desired, portrait, imageAspect);
        const placement = resized.placements[0];

        expect(desired).toBeCloseTo(0.5333333333);
        expect(placement.width).toBeCloseTo(0.3);
        expect(placement.height).toBeCloseTo(0.05625);
        expect((placement.width * portrait.width) / (placement.height * portrait.height)).toBeCloseTo(imageAspect);
        expect(placement.x + placement.width).toBeLessThanOrEqual(1);
        expect(placement.y + placement.height).toBeLessThanOrEqual(1);
    });
});

describe("unified placement state", () => {
    it("initializes preloaded placements in the same editable collection", () => {
        const source = [{ page: 1, x: 0.1, y: 0.2, width: 0.4, height: 0.075 }];
        const state = initializePlacements(source);

        expect(state.placements[0]).toEqual({ id: 1, ...source[0] });
        expect(serializedPlacements(state)).toEqual(source);
        expect(state.selectedId).toBeNull();
        expect(initializePlacements([]).placements).toEqual([]);
    });

    it("selects only existing items and clears selection when removing", () => {
        const initial = initializePlacements([
            { page: 1, x: 0.1, y: 0.2, width: 0.4, height: 0.075 },
            { page: 1, x: 0.2, y: 0.4, width: 0.4, height: 0.075 },
        ]);

        const selected = selectPlacement(initial, 2);
        expect(selected.selectedId).toBe(2);
        expect(selectPlacement(selected, 99).selectedId).toBeNull();
        expect(removeSelectedPlacement(selected).placements.map(({ id }) => id)).toEqual([1]);
        expect(removeSelectedPlacement(selected).selectedId).toBeNull();
        expect(removePlacement(selected, 1).selectedId).toBe(2);
    });

    it("requires a nonempty, bounded, aspect-correct collection on known pages", () => {
        const pages = new Map([[1, portrait]]);
        const valid = initializePlacements([
            { page: 1, x: 0.1, y: 0.2, width: 0.4, height: 0.075 },
        ]);
        const distorted = initializePlacements([
            { page: 1, x: 0.1, y: 0.2, width: 0.4, height: 0.2 },
        ]);

        expect(isPlacementStateValid(valid, 1, pages, imageAspect)).toBe(true);
        expect(isPlacementStateValid(initializePlacements([]), 1, pages, imageAspect)).toBe(false);
        expect(isPlacementStateValid(distorted, 1, pages, imageAspect)).toBe(false);
        expect(isPlacementStateValid(valid, 1, new Map(), imageAspect)).toBe(false);
    });
});
