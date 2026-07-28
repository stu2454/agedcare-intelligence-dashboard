// Copies the bundled quarterly extract from the repo root into public/ before
// a build, so the workbook lives in exactly one place in version control.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(here, "..", "..");
const filename = "star-ratings-quarterly-data-extract-february-2025.xlsx";

const source = join(repoRoot, filename);
const targetDir = join(here, "..", "public");
const target = join(targetDir, filename);

if (!existsSync(source)) {
  console.error(`[copy-data] Missing extract at ${source}`);
  process.exit(1);
}

mkdirSync(targetDir, { recursive: true });
copyFileSync(source, target);
console.log(`[copy-data] Copied ${filename} into public/`);
