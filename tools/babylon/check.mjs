// Plays an asset in Babylon.js, a real KHR_interactivity implementation, without a browser.
//
//   node tools/babylon/check.mjs ASSET.glb [--click NODE --moves NODE]
//
// Fails if Babylon rejects any behavior graph or logs an error while loading. With --click,
// it selects that node the way a pointer tap would, runs a second of frames, and fails
// unless the --moves node's rotation changed.
import fs from "node:fs";
import { AppendSceneAsync, FreeCamera, Logger, NullEngine, PickingInfo, Quaternion, Scene, Vector3 } from "@babylonjs/core";
import "@babylonjs/loaders/glTF/index.js";
import { GetKHRInteractivityImportResults } from "@babylonjs/loaders/glTF/2.0/Extensions/KHR_interactivity.pure.js";

// Node has no PointerEvent; Babylon's simulated pointer input only needs the fields it copies
globalThis.PointerEvent ??= class extends Event {
    constructor(type, init = {}) {
        super(type);
        Object.assign(this, init);
    }
};

const args = process.argv.slice(2);
const option = (name) => (args.includes(name) ? args[args.indexOf(name) + 1] : undefined);
const file = args[0];
const errors = [];
const original = Logger.Error;
Logger.Error = (m) => {
    errors.push(Array.isArray(m) ? JSON.stringify(m) : String(m));
};
Logger.Warn = () => {};
Logger.Log = () => {};

const scene = new Scene(new NullEngine());
new FreeCamera("camera", new Vector3(0, 1, -5), scene);
await AppendSceneAsync(new Uint8Array(fs.readFileSync(file)), scene, { pluginExtension: ".glb" });
for (let i = 0; i < 3; i++) scene.render();
let failed = errors.length > 0;
for (const e of errors) original(`${file}: ${e}`);
// what Babylon made of each graph: its diagnostics, and which declarations it treats as no-ops
for (const result of GetKHRInteractivityImportResults(scene) ?? []) {
    for (const g of result.graphs) {
        for (const d of g.diagnostics) console.log(`${file}: graph ${g.graph.index} ${d.severity}: ${d.path ?? ""} ${d.message}`);
        g.graph.declarations?.forEach((d, i) => {
            if (d.support !== "supported") console.log(`${file}: graph ${g.graph.index} declaration ${i} (${d.source?.op}): ${d.support}`);
        });
    }
}

const clickName = option("--click");
if (clickName) {
    const target = scene.meshes.find((m) => m.name === clickName);
    const watch = [...scene.transformNodes, ...scene.meshes].find((n) => n.name === option("--moves"));
    if (!target || !watch) {
        console.error(`${file}: no node named ${!target ? clickName : option("--moves")}`);
        process.exit(1);
    }
    const rotation = () => watch.rotationQuaternion.clone(); // the glTF loader always sets it
    const before = rotation();
    const pick = new PickingInfo();
    pick.hit = true;
    pick.pickedMesh = target;
    pick.pickedPoint = target.getAbsolutePosition();
    scene.simulatePointerDown(pick);
    scene.simulatePointerUp(pick);
    let moved = 0;
    for (let f = 0; f < 30; f++) {
        await new Promise((r) => setTimeout(r, 1000 / 30));
        scene.render();
        moved = Math.max(moved, 1 - Math.abs(Quaternion.Dot(before, rotation())));
    }
    console.log(`${file}: selecting ${clickName} ${moved > 1e-3 ? "moved" : "did not move"} ${watch.name}`);
    failed ||= moved <= 1e-3;
}
console.log(`${file}: ${failed ? "FAILED in Babylon.js" : "plays in Babylon.js"}`);
process.exit(failed ? 1 : 0);
