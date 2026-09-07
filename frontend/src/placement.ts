export interface Placement {
    page: number;
    x: number;
    y: number;
    width: number;
    height: number;
}

export interface EditablePlacement extends Placement {
    id: number;
}

export interface PlacementState {
    placements: EditablePlacement[];
    selectedId: number | null;
    nextId: number;
}

export interface NormalizedPoint {
    x: number;
    y: number;
}

export interface PageSize {
    width: number;
    height: number;
}

const MIN_PLACEMENT_WIDTH = 0.001;
const ASPECT_RATIO_TOLERANCE = 0.05;

function clamp(value: number, minimum: number, maximum: number): number {
    return Math.min(Math.max(value, minimum), maximum);
}

function replacePlacement(
    state: PlacementState,
    id: number,
    update: (placement: EditablePlacement) => EditablePlacement,
): PlacementState {
    return {
        ...state,
        placements: state.placements.map((placement) =>
            placement.id === id ? update(placement) : placement,
        ),
    };
}

export function initializePlacements(initial: Placement[]): PlacementState {
    return {
        placements: initial.map((placement, index) => ({
            ...placement,
            id: index + 1,
        })),
        selectedId: null,
        nextId: initial.length + 1,
    };
}

export function normalizedHeight(
    width: number,
    imageAspect: number,
    page: PageSize,
): number {
    return (width / imageAspect) * (page.width / page.height);
}

export function centeredPlacement(
    pageNumber: number,
    center: NormalizedPoint,
    configuredWidth: number,
    page: PageSize,
    imageAspect: number,
): Placement {
    const maximumWidth = Math.min(1, imageAspect * (page.height / page.width));
    const width = clamp(configuredWidth, MIN_PLACEMENT_WIDTH, maximumWidth);
    const height = Math.min(normalizedHeight(width, imageAspect, page), 1);
    return {
        page: pageNumber,
        x: clamp(center.x - width / 2, 0, 1 - width),
        y: clamp(center.y - height / 2, 0, 1 - height),
        width,
        height,
    };
}

export function addPlacement(
    state: PlacementState,
    pageNumber: number,
    center: NormalizedPoint,
    configuredWidth: number,
    page: PageSize,
    imageAspect: number,
): PlacementState {
    const placement: EditablePlacement = {
        id: state.nextId,
        ...centeredPlacement(pageNumber, center, configuredWidth, page, imageAspect),
    };
    return {
        placements: [...state.placements, placement],
        selectedId: placement.id,
        nextId: state.nextId + 1,
    };
}

export function movePlacement(
    state: PlacementState,
    id: number,
    x: number,
    y: number,
): PlacementState {
    return replacePlacement(state, id, (placement) => ({
        ...placement,
        x: clamp(x, 0, 1 - placement.width),
        y: clamp(y, 0, 1 - placement.height),
    }));
}

export function resizePlacement(
    state: PlacementState,
    id: number,
    desiredWidth: number,
    page: PageSize,
    imageAspect: number,
): PlacementState {
    return replacePlacement(state, id, (placement) => {
        const aspectHeight = normalizedHeight(1, imageAspect, page);
        const maximumWidth = Math.min(
            1 - placement.x,
            (1 - placement.y) / aspectHeight,
        );
        const width = clamp(desiredWidth, MIN_PLACEMENT_WIDTH, maximumWidth);
        return {
            ...placement,
            width,
            height: Math.min(width * aspectHeight, 1 - placement.y),
        };
    });
}

export function desiredResizeWidth(
    placement: Placement,
    start: NormalizedPoint,
    current: NormalizedPoint,
    page: PageSize,
    imageAspect: number,
): number {
    const horizontal = placement.width + current.x - start.x;
    const vertical =
        placement.width +
        (current.y - start.y) * imageAspect * (page.height / page.width);
    return Math.abs(horizontal - placement.width) >=
        Math.abs(vertical - placement.width)
        ? horizontal
        : vertical;
}

export function selectPlacement(
    state: PlacementState,
    id: number | null,
): PlacementState {
    return {
        ...state,
        selectedId:
            id !== null && state.placements.some((placement) => placement.id === id)
                ? id
                : null,
    };
}

export function removePlacement(
    state: PlacementState,
    id: number,
): PlacementState {
    return {
        ...state,
        placements: state.placements.filter((placement) => placement.id !== id),
        selectedId: state.selectedId === id ? null : state.selectedId,
    };
}

export function removeSelectedPlacement(state: PlacementState): PlacementState {
    return state.selectedId === null
        ? state
        : removePlacement(state, state.selectedId);
}

export function serializedPlacements(state: PlacementState): Placement[] {
    return state.placements.map(({ id: _id, ...placement }) => placement);
}

export function aspectMismatchedPlacementPages(
    state: PlacementState,
    pages: ReadonlyMap<number, PageSize>,
    imageAspect: number,
): number[] {
    if (!Number.isFinite(imageAspect) || imageAspect <= 0) {
        return [];
    }
    const affectedPages = new Set<number>();
    for (const placement of state.placements) {
        const page = pages.get(placement.page);
        if (
            page === undefined ||
            ![placement.width, placement.height].every(Number.isFinite) ||
            placement.width <= 0 ||
            placement.height <= 0
        ) {
            continue;
        }
        const physicalAspect =
            (placement.width * page.width) / (placement.height * page.height);
        if (Math.abs(physicalAspect - imageAspect) / imageAspect > ASPECT_RATIO_TOLERANCE) {
            affectedPages.add(placement.page);
        }
    }
    return [...affectedPages].sort((first, second) => first - second);
}

export function isPlacementStateValid(
    state: PlacementState,
    pageCount: number,
    pages: ReadonlyMap<number, PageSize>,
    imageAspect: number,
): boolean {
    if (
        state.placements.length === 0 ||
        !Number.isInteger(pageCount) ||
        pageCount < 1 ||
        !Number.isFinite(imageAspect) ||
        imageAspect <= 0
    ) {
        return false;
    }
    return state.placements.every((placement) => {
        const page = pages.get(placement.page);
        if (
            page === undefined ||
            !Number.isInteger(placement.page) ||
            placement.page < 1 ||
            placement.page > pageCount ||
            ![placement.x, placement.y, placement.width, placement.height].every(
                Number.isFinite,
            ) ||
            placement.x < 0 ||
            placement.y < 0 ||
            placement.width <= 0 ||
            placement.height <= 0 ||
            placement.x + placement.width > 1 ||
            placement.y + placement.height > 1
        ) {
            return false;
        }
        const physicalAspect =
            (placement.width * page.width) / (placement.height * page.height);
        return (
            Math.abs(physicalAspect - imageAspect) / imageAspect <=
            ASPECT_RATIO_TOLERANCE
        );
    });
}
