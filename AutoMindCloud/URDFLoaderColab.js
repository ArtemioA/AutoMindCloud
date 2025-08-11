// AutoMindCloud/URDFLoaderColab.js
// Serve via jsDelivr:
//   https://cdn.jsdelivr.net/gh/ArtemioA/AutoMindCloud/AutoMindCloud/URDFLoaderColab.js

const SRC = {
  three: "https://cdn.jsdelivr.net/npm/three@0.127.0/build/three.module.js",
  orbit: "https://cdn.jsdelivr.net/npm/three@0.127.0/examples/jsm/controls/OrbitControls.js",
  stl:   "https://cdn.jsdelivr.net/npm/three@0.127.0/examples/jsm/loaders/STLLoader.js",
  urdf:  "https://cdn.jsdelivr.net/npm/urdf-loader@0.10.1/src/URDFLoader.js"
};

async function loadDeps() {
  const [
    t,
    { OrbitControls },
    { STLLoader },
    { default: URDFLoader }
  ] = await Promise.all([
    import(SRC.three),
    import(SRC.orbit),
    import(SRC.stl),
    import(SRC.urdf),
  ]);
  const {
    Scene, PerspectiveCamera, WebGLRenderer, DirectionalLight, AmbientLight,
    HemisphereLight, GridHelper, Color, PCFSoftShadowMap, sRGBEncoding,
    ACESFilmicToneMapping, Mesh, MeshStandardMaterial, DoubleSide
  } = t;
  return {
    Scene, PerspectiveCamera, WebGLRenderer, DirectionalLight, AmbientLight,
    HemisphereLight, GridHelper, Color, PCFSoftShadowMap, sRGBEncoding,
    ACESFilmicToneMapping, Mesh, MeshStandardMaterial, DoubleSide,
    OrbitControls, STLLoader, URDFLoader
  };
}

// ---------- helpers ----------
function b64ToUint8(b64) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}
function b64ToText(b64) {
  return new TextDecoder().decode(b64ToUint8(b64));
}
function dataUrlFromBase64(b64, mime = "model/stl") {
  return `data:${mime};base64,${b64}`;
}
function rewriteUrdfMeshFilenames(urdfText, mapping) {
  return urdfText.replace(/<mesh\s+filename="([^"]+)"/gi, (_, filename) => {
    const base = filename.split("/").pop();
    const url = mapping[filename] || mapping[base];
    return `<mesh filename="${url || filename}"`;
  });
}
function defaults(over = {}) {
  return {
    upAxis: "z",
    initialDistance: 12,
    castShadows: true,
    background: "#0b0b0b",
    showGrid: true,
    ...over
  };
}

// ---------- main ----------
export default async function initViewer(container) {
  if (!container) throw new Error("initViewer(container) requires a container element");
  const {
    Scene, PerspectiveCamera, WebGLRenderer, DirectionalLight, AmbientLight,
    HemisphereLight, GridHelper, Color, PCFSoftShadowMap, sRGBEncoding,
    ACESFilmicToneMapping, Mesh, MeshStandardMaterial, DoubleSide,
    OrbitControls, STLLoader, URDFLoader
  } = await loadDeps();

  // Scene / Renderer
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

  // Camera / Controls
  const camera = new PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.01, 2000);
  camera.position.set(12, 12, 12);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.target.set(0, 0, 0);

  // Lights & Grid
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
    const el = renderer.domElement;
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  async function loadFromPayload(payload) {
    if (!payload || typeof payload !== "object") throw new Error("Invalid payload");
    const opts = defaults(payload.options);

    // Up axis
    camera.up.set(0, opts.upAxis === "z" ? 0 : 1, opts.upAxis === "z" ? 1 : 0);

    // ---- Rebuild URDF text from base64 or plain text
    let urdfText = "";
    if (payload.urdf_b64) {
      urdfText = b64ToText(payload.urdf_b64);
    } else if (typeof payload.urdf === "string") {
      urdfText = payload.urdf;
    } else {
      throw new Error("Payload missing 'urdf' text or 'urdf_b64'.");
    }

    // ---- Build mesh data URLs from base64
    // payload.meshes should be: { "<basename or original ref>": "<base64>" }
    const meshUrlMap = {};
    for (const [k, b64] of Object.entries(payload.meshes || {})) {
      meshUrlMap[k] = dataUrlFromBase64(b64, "model/stl");
    }

    // ---- Rewrite URDF mesh refs to our data URLs
    const urdfTextRewritten = rewriteUrdfMeshFilenames(urdfText, meshUrlMap);

    // ---- Create a Blob URL for the URDF file (just for URDFLoader to fetch)
    const urdfBlob = new Blob([urdfTextRewritten], { type: "text/xml" });
    const urdfUrl = URL.createObjectURL(urdfBlob);

    // Loaders
    const stlLoader = new STLLoader();
    const urdfLoader = new URDFLoader();

    // IMPORTANT: URDFLoader expects an Object3D from loadMeshCb.
    // If we see a data:model/stl;base64 URL, decode and use STLLoader.parse().
    urdfLoader.loadMeshCb = function (path, manager, onComplete) {
      const url = String(path || "");
      const isDataStl = url.startsWith("data:model/stl;base64,");
      const isStlExt  = /\.stl(\?.*)?$/i.test(url);

      if (isDataStl) {
        try {
          const b64 = url.split(",")[1] || "";
          const buffer = b64ToUint8(b64).buffer;
          const geometry = stlLoader.parse(buffer);       // parse in-memory
          if (geometry.attributes?.normal == null) {
            geometry.computeVertexNormals();
          }
          const mat = new MeshStandardMaterial({
            color: 0x999999, metalness: 0.1, roughness: 0.8, side: DoubleSide
          });
          const mesh = new Mesh(geometry, mat);
          mesh.castShadow = mesh.receiveShadow = true;
          onComplete(mesh);
        } catch (e) {
          console.error("STL parse error:", e);
          onComplete(null);
        }
        return;
      }

      if (isStlExt) {
        // (Not used in our data-URL flow, but keep as fallback.)
        stlLoader.load(url, geometry => {
          try {
            if (geometry.attributes?.normal == null) geometry.computeVertexNormals();
            const mat = new MeshStandardMaterial({
              color: 0x999999, metalness: 0.1, roughness: 0.8, side: DoubleSide
            });
            const mesh = new Mesh(geometry, mat);
            mesh.castShadow = mesh.receiveShadow = true;
            onComplete(mesh);
          } catch (e) {
            console.error("STL post-load error:", e);
            onComplete(null);
          }
        }, undefined, err => {
          console.error("STL load error:", url, err);
          onComplete(null);
        });
        return;
      }

      console.warn("Unsupported mesh path:", url);
      onComplete(null);
    };

    // Clear previous robot if any
    if (robot) { scene.remove(robot); robot = null; }

    // Camera distance
    const dist = Math.max(0.1, Number(opts.initialDistance) || 12);
    camera.position.set(dist, dist, dist);

    // Load URDF
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

  // Resize
  function onResize() {
    const w = container.clientWidth || window.innerWidth;
    const h = container.clientHeight || window.innerHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
  }
  window.addEventListener("resize", onResize);
  onResize();

  return { scene, camera, renderer, controls, loadFromPayload, setBackground, setGrid, dispose };
}
