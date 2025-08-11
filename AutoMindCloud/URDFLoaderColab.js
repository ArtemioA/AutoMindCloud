// AutoMindCloud/URDFLoaderColab.js
// This version uses BARE imports. Your HTML/Colab page must include an <script type="importmap">.
// See the Colab cell I gave you previously for the importmap block.

import {
  Scene, PerspectiveCamera, WebGLRenderer, DirectionalLight, AmbientLight,
  HemisphereLight, GridHelper, Color, PCFSoftShadowMap, sRGBEncoding, ACESFilmicToneMapping
} from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
// Optional DAE support can be lazy-imported inside loadMeshCb if needed.
// import { ColladaLoader } from "three/examples/jsm/loaders/ColladaLoader.js";
import URDFLoader from "urdf-loader";

// ---------- helpers ----------
function b64ToBlobUrl(b64, mime = "model/stl") {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const blob = new Blob([bytes], { type: mime });
  return URL.createObjectURL(blob);
}

function rewriteUrdfMeshFilenames(urdfText, mapping) {
  return urdfText.replace(/<mesh\s+filename="([^"]+)"/gi, (_, filename) => {
    const base = filename.split("/").pop();
    const url = mapping[filename] || mapping[base];
    return `<mesh filename="${url || filename}"`;
  });
}

// Normalize URLs that get mangled by URDFLoader resolution, e.g.
// "blob:https://.../blob:https://.../<uuid>" -> "blob:https://.../<uuid>"
function normalizeUrl(p) {
  const s = String(p || "");
  const lastBlob = s.lastIndexOf("blob:");
  const lastData = s.lastIndexOf("data:");
  if (lastBlob > 0) return s.slice(lastBlob);
  if (lastData > 0) return s.slice(lastData);
  return s;
}

function defaults(overrides = {}) {
  return {
    upAxis: "z",
    initialDistance: 10,
    castShadows: true,
    background: "#0b0b0b",
    showGrid: true,
    ...overrides
  };
}

// ---------- main ----------
export default async function initViewer(container) {
  if (!container) throw new Error("initViewer(container): container element is required.");

  // Scene & renderer
  const scene = new Scene();
  scene.background = new Color("#0b0b0b");

  const renderer = new WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.setSize(container.clientWidth, container.clientHeight, false);
  renderer.outputEncoding = sRGBEncoding;
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = PCFSoftShadowMap;
  container.appendChild(renderer.domElement);

  // Camera & controls
  const camera = new PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.01, 2000);
  camera.position.set(10, 10, 10);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.target.set(0, 0, 0);

  // Lights & grid
  scene.add(new HemisphereLight(0xffffff, 0x444444, 0.6));
  const dir = new DirectionalLight(0xffffff, 1.0);
  dir.position.set(5, 10, 7);
  dir.castShadow = true;
  dir.shadow.mapSize.set(1024, 1024);
  scene.add(dir);
  scene.add(new AmbientLight(0xffffff, 0.2));

  const grid = new GridHelper(10, 20, 0x444444, 0x222222);
  grid.visible = true;
  scene.add(grid);

  let robot = null;

  function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }
  animate();

  function setBackground(color) { scene.background = new Color(color); }
  function setGrid(visible) { grid.visible = !!visible; }
  function dispose() {
    renderer.dispose();
    if (renderer.domElement?.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement);
  }

  async function loadUrdfFromPayload(payload) {
    if (!payload || typeof payload !== "object") throw new Error("Invalid payload");
    const opts = defaults(payload.options);

    // Up axis
    camera.up.set(0, opts.upAxis === "z" ? 0 : 1, opts.upAxis === "z" ? 1 : 0);

    // Build blob URLs for STLs
    const meshUrlMap = {};
    for (const [name, b64] of Object.entries(payload.meshes || {})) {
      meshUrlMap[name] = b64ToBlobUrl(b64, "model/stl");
    }

    // Rewrite URDF mesh filenames to blob URLs
    const urdfText = rewriteUrdfMeshFilenames(payload.urdf || "", meshUrlMap);
    const urdfBlob = new Blob([urdfText], { type: "text/xml" });
    const urdfUrl = URL.createObjectURL(urdfBlob);

    // Loaders
    const stlLoader = new STLLoader();
    const urdfLoader = new URDFLoader();

    // Accept STL from .stl, blob:, and data:model/stl; normalize "double-blob" URLs from URDFLoader
    urdfLoader.loadMeshCb = async function (path, manager, onComplete) {
      let p = normalizeUrl(path);

      const isBlob = p.startsWith("blob:");
      const isDataStl = p.startsWith("data:model/stl");
      const isStlExt = /\.stl(\?.*)?$/i.test(p);

      if (isStlExt || isBlob || isDataStl) {
        stlLoader.load(
          p,
          geometry => onComplete(geometry),
          undefined,
          err => {
            console.error("STL load error:", p, err);
            onComplete(null);
          }
        );
        return;
      }

      // OPTIONAL: enable DAE if your URDF references .dae files
      // if (/\.dae(\?.*)?$/i.test(p)) {
      //   const { ColladaLoader } = await import("three/examples/jsm/loaders/ColladaLoader.js");
      //   const daeLoader = new ColladaLoader();
      //   daeLoader.load(
      //     p,
      //     collada => onComplete(collada.scene),
      //     undefined,
      //     err => {
      //       console.error("DAE load error:", p, err);
      //       onComplete(null);
      //     }
      //   );
      //   return;
      // }

      console.warn("Unsupported mesh type:", p);
      onComplete(null);
    };

    // Clear previous robot
    if (robot) { scene.remove(robot); robot = null; }

    // Camera distance
    const dist = Math.max(0.1, Number(opts.initialDistance) || 10);
    camera.position.set(dist, dist, dist);

    await new Promise((resolve, reject) => {
      urdfLoader.load(
        urdfUrl,
        (urdf) => {
          robot = urdf;

          if (opts.castShadows) {
            robot.traverse(obj => {
              if (obj && 'castShadow' in obj) obj.castShadow = true;
              if (obj && 'receiveShadow' in obj) obj.receiveShadow = true;
            });
          }

          if (opts.upAxis !== "z") robot.rotation.x = -Math.PI / 2;

          controls.target.set(0, 0, 0);
          controls.update();

          scene.add(robot);
          resolve();
        },
        undefined,
        reject
      );
    });

    setBackground(opts.background);
    setGrid(!!opts.showGrid);
    console.log("[Viewer] URDF loaded. Embedded STL files:", Object.keys(payload.meshes || {}).length);
  }

  function onResize() {
    const w = container.clientWidth || window.innerWidth;
    const h = container.clientHeight || window.innerHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
  }
  window.addEventListener("resize", onResize);
  onResize();

  return { scene, camera, renderer, controls, loadUrdfFromPayload, setBackground, setGrid, dispose };
}
