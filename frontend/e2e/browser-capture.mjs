import { writeFileSync } from "node:fs";

const capturePath = process.env.PDF_SIGNOFF_BROWSER_CAPTURE;
const url = process.argv.at(-1);

if (capturePath === undefined || url === undefined) {
    process.exitCode = 2;
} else {
    writeFileSync(capturePath, url, "utf8");
}
