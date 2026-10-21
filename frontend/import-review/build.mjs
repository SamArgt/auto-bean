import { build } from "esbuild";
import { readFile, writeFile, readdir } from "node:fs/promises";
import { createHash } from "node:crypto";
const root = new URL("../../plugins/auto-bean/ui/", import.meta.url);
const output = await build({
  entryPoints: ["src/main.tsx"],
  bundle: true,
  write: false,
  minify: true,
  format: "iife",
  target: "es2022",
  outfile: "panel.js",
});
const js = output.outputFiles.find((f) => f.path.endsWith(".js")).text;
const css = output.outputFiles.find((f) => f.path.endsWith(".css"))?.text ?? "";
const html =
  '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Import Review</title><style>' +
  css +
  '</style></head><body><div id="root"></div><script>' +
  js.replaceAll("</script", "<\\/script") +
  "</script></body></html>";
await writeFile(new URL("bundle.html", root), html);
const hash = (b) => createHash("sha256").update(b).digest("hex");
const inputs = {};
for (const file of [
  "package.json",
  "package-lock.json",
  "tsconfig.json",
  "build.mjs",
  ...(await readdir("src")).sort().map((f) => "src/" + f),
])
  inputs[file] = hash(await readFile(file));
await writeFile(
  new URL("build.json", root),
  JSON.stringify(
    { schema_version: 1, inputs, bundle_sha256: hash(html) },
    null,
    2,
  ) + "\n",
);
