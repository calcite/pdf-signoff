import { expect, test, type Page } from "@playwright/test";
import type { ChildProcessWithoutNullStreams } from "node:child_process";
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

interface ProcessResult {
    code: number | null;
    signal: NodeJS.Signals | null;
    stderr: string;
    stdout: string;
}

interface Placement {
    page: number;
    x: number;
    y: number;
    width: number;
    height: number;
}

const frontendDirectory = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repository = resolve(frontendDirectory, "..");
const executable = join(repository, ".venv", "bin", "pdf-signoff");
const python = join(repository, ".venv", "bin", "python");
const fixtureFactory = join(repository, "tests", "e2e", "create_review_fixture.py");
const browserCapture = join(frontendDirectory, "e2e", "browser-capture.mjs");

function createFixtureDirectory(): string {
    const directory = mkdtempSync(join(tmpdir(), "pdf-signoff-e2e-"));
    const created = spawnSync(python, [fixtureFactory, directory], {
        cwd: repository,
        encoding: "utf8",
    });
    expect(created.status, created.stderr).toBe(0);
    return directory;
}

function startCli(directory: string, withProfile: boolean): {
    capturePath: string;
    child: ChildProcessWithoutNullStreams;
    completed: Promise<ProcessResult>;
    output: string;
} {
    const capturePath = join(directory, "browser-url.txt");
    const output = join(directory, "output.pdf");
    const args = [
        join(directory, "input.pdf"),
        "--signature",
        join(directory, "signature.png"),
        "--output",
        output,
    ];
    if (withProfile) {
        args.push("--coords", join(directory, "profile.json"));
    }
    const browserCommand = `${JSON.stringify(process.execPath)} ${JSON.stringify(browserCapture)} %s`;
    const child = spawn(executable, args, {
        cwd: repository,
        env: {
            ...process.env,
            BROWSER: browserCommand,
            HOME: join(directory, "home"),
            PDF_SIGNOFF_BROWSER_CAPTURE: capturePath,
            XDG_CONFIG_HOME: join(directory, "xdg"),
        },
        stdio: "pipe",
    });
    let stdout = "";
    let stderr = "";
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk: string) => (stdout += chunk));
    child.stderr.on("data", (chunk: string) => (stderr += chunk));
    const completed = new Promise<ProcessResult>((resolveResult, reject) => {
        child.on("error", reject);
        child.on("close", (code, signal) => {
            resolveResult({ code, signal, stderr, stdout });
        });
    });
    return { capturePath, child, completed, output };
}

async function waitForReviewUrl(capturePath: string): Promise<string> {
    await expect
        .poll(() => existsSync(capturePath), {
            message: "configured browser command did not receive the review URL",
        })
        .toBe(true);
    return readFileSync(capturePath, "utf8");
}

async function openReview(page: Page, capturePath: string): Promise<string> {
    const url = await waitForReviewUrl(capturePath);
    await page.goto(url);
    await expect(page.locator(".pdf-page")).toBeVisible();
    return url;
}

test("preload edits become the stamped output and sole emitted profile", async ({ page }) => {
    const directory = createFixtureDirectory();
    const process = startCli(directory, true);
    let downloads = 0;
    let fileChoosers = 0;
    let submitted: Placement[] | undefined;
    page.on("download", () => downloads++);
    page.on("filechooser", () => fileChoosers++);
    page.on("dialog", (dialog) => {
        throw new Error(`Unexpected browser dialog: ${dialog.type()}`);
    });
    page.on("request", (request) => {
        if (request.url().endsWith("/api/save")) {
            submitted = (request.postDataJSON() as { placements: Placement[] }).placements;
        }
    });

    try {
        const tokenizedUrl = await openReview(page, process.capturePath);
        const overlay = page.locator(".signature-overlay");
        await expect(overlay).toHaveCount(1);
        const initialStyle = await overlay.getAttribute("style");

        const dragBox = await overlay.boundingBox();
        expect(dragBox).not.toBeNull();
        await page.mouse.move(dragBox!.x + dragBox!.width / 2, dragBox!.y + dragBox!.height / 2);
        await page.mouse.down();
        await page.mouse.move(dragBox!.x + dragBox!.width / 2 + 90, dragBox!.y + dragBox!.height / 2 + 55);
        await page.mouse.up();
        await expect(overlay).not.toHaveAttribute("style", initialStyle!);

        const handle = overlay.locator(".resize-handle");
        const movedStyle = await overlay.getAttribute("style");
        const handleBox = await handle.boundingBox();
        expect(handleBox).not.toBeNull();
        await page.mouse.move(handleBox!.x + handleBox!.width / 2, handleBox!.y + handleBox!.height / 2);
        await page.mouse.down();
        await page.mouse.move(handleBox!.x + handleBox!.width / 2 + 65, handleBox!.y + handleBox!.height / 2 + 15);
        await page.mouse.up();
        await expect(overlay).not.toHaveAttribute("style", movedStyle!);
        const resizedBox = await overlay.boundingBox();
        expect(resizedBox).not.toBeNull();

        await overlay.click({ button: "right" });
        await page.getByRole("menuitem", { name: "Remove signature" }).click();
        await expect(overlay).toHaveCount(0);
        await expect(page.getByRole("button", { name: "Save" })).toBeDisabled();

        await page.getByRole("button", { name: "Place signature" }).click();
        const pdfPage = page.locator(".pdf-page");
        const pageBox = await pdfPage.boundingBox();
        expect(pageBox).not.toBeNull();
        await page.mouse.move(pageBox!.x + 600, pageBox!.y + 575);
        const preview = page.locator(".signature-preview");
        await expect(preview).toHaveCount(1);
        const previewBox = await preview.boundingBox();
        expect(previewBox).not.toBeNull();
        expect(previewBox!.width).toBeCloseTo(resizedBox!.width, 1);
        await pdfPage.click({ position: { x: 600, y: 575 } });
        await expect(overlay).toHaveCount(1);
        const newBox = await overlay.boundingBox();
        expect(newBox).not.toBeNull();
        expect(newBox!.width).toBeCloseTo(resizedBox!.width, 1);
        await expect(page.getByRole("button", { name: "Save" })).toBeEnabled();

        await page.getByRole("button", { name: "Save" }).click();
        await expect(page.locator(".saved")).toHaveText("Saved");
        const result = await process.completed;

        expect(result.code).toBe(0);
        expect(result.signal).toBeNull();
        expect(result.stdout.endsWith("\n")).toBe(true);
        expect(result.stdout.trim().split("\n")).toHaveLength(1);
        const emitted = JSON.parse(result.stdout) as {
            placements: Placement[];
            match: { required_text: Array<{ text: string }> };
        };
        expect(submitted).toBeDefined();
        expect(emitted.placements).toEqual(submitted);
        expect(emitted.placements).toHaveLength(1);
        expect(emitted.placements[0].x).toBeGreaterThan(0.5);
        expect(emitted.match.required_text[0].text).toBe(
            "Approval form for browser review",
        );
        expect(statSync(process.output).size).toBeGreaterThan(0);
        const inspection = spawnSync(
            python,
            [
                "-c",
                "import pymupdf,sys; d=pymupdf.open(sys.argv[1]); print(len(d[0].get_images())); d.close()",
                process.output,
            ],
            { encoding: "utf8" },
        );
        expect(inspection.status, inspection.stderr).toBe(0);
        expect(inspection.stdout.trim()).toBe("1");
        expect(result.stderr).toContain("Review session opened in the browser");
        expect(result.stderr).toContain(`Saved signed PDF: ${process.output}`);
        expect(result.stderr).not.toContain(tokenizedUrl.split("token=", 2)[1]);
        expect(downloads).toBe(0);
        expect(fileChoosers).toBe(0);
    } finally {
        if (process.child.exitCode === null) {
            process.child.kill("SIGINT");
            await process.completed;
        }
        rmSync(directory, { recursive: true, force: true });
    }
});

test("an empty session has no download and keeps waiting after browser close", async ({ page }) => {
    const directory = createFixtureDirectory();
    const process = startCli(directory, false);
    let downloads = 0;
    let fileChoosers = 0;
    page.on("download", () => downloads++);
    page.on("filechooser", () => fileChoosers++);

    try {
        await openReview(page, process.capturePath);
        await expect(page.locator(".signature-overlay")).toHaveCount(0);
        await expect(page.getByRole("button", { name: "Save" })).toBeDisabled();
        await page.close();
        await new Promise((resolveDelay) => setTimeout(resolveDelay, 300));
        expect(process.child.exitCode).toBeNull();

        process.child.kill("SIGINT");
        const result = await process.completed;
        expect(result.code).toBe(1);
        expect(result.signal).toBeNull();
        expect(result.stdout).toBe("");
        expect(result.stderr).toContain("Review interrupted; no profile was emitted.");
        expect(result.stderr).toContain("Aborted!");
        expect(existsSync(process.output)).toBe(false);
        expect(
            readdirSync(directory).filter((name) => name.startsWith(".output.pdf.") && name.endsWith(".tmp")),
        ).toEqual([]);
        expect(downloads).toBe(0);
        expect(fileChoosers).toBe(0);
    } finally {
        if (process.child.exitCode === null) {
            process.child.kill("SIGKILL");
            await process.completed;
        }
        rmSync(directory, { recursive: true, force: true });
    }
});
