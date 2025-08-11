// AutoMindCloud/URDFLoaderColab.js
// Serve via jsDelivr:
//   https://cdn.jsdelivr.net/gh/ArtemioA/AutoMindCloud/AutoMindCloud/URDFLoaderColab.js

const IMPORT_MAP = {
  three: "https://cdn.jsdelivr.net/npm/three@0.127.0/build/three.module.js",
  controls: "https://cdn.jsdelivr.net/npm/three@0.127.0/examples/jsm/controls/OrbitControls.js",
  stlloader: "https://cdn.jsdelivr.net/npm/three@0.127.0/examples/jsm/loaders/STLLoader.js",
  urdf: "https://cdn.jsdelivr.net/npm/urdf-loader@0.10.1/src/URDFLoader.js"
};

async function loadModules() {
  const [
    { Scene, PerspectiveCamera, WebGLRenderer, DirectionalLight, AmbientLight, PCFSoftShadowMap, Color, sRGBEncoding, ACESFilmicToneMapping, GridHelper, HemisphereLight, Vector3 },
    { OrbitControls },
    { STLLoader },
    { default: URDFLoader }
  ] = await Promise.all([
    import(IMPORT_MAP.three),
    import(IMPORT_MAP.controls),
    import(IMPORT_MAP.stlloader),
    import(IMPORT_MAP.urdf)
  ]);
  return { Scene, PerspectiveCamera, WebGLRenderer, DirectionalLight, AmbientLight, PCFSoftShadowMap, Color, sRGBEncoding, ACESFilmicToneMapping, GridHelper, HemisphereLight, Vector3, OrbitControls, STLLoader, URDFLoader };
}

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

function defaultOptions(user) {
  return {
    upAxis: "z",            // "z" or "y"
    initialDistance: 6.0,
    castShadows: true,
    background: "#0b0b0b",
    showGrid: true,
    ...user
  };
}

export default async function initViewer(container) {
  if (!container) throw new Error("initViewer(container): container is required.");
  const { Scene, PerspectiveCamera, WebGLRenderer, DirectionalLight, AmbientLight, PCFSoftShadowMap, Color, sRGBEncoding, ACESFilmicToneMapping, GridHelper, HemisphereLight, Vector3, OrbitControls, STLLoader, URDFLoader } = await loadModules();

  const scene = new Scene();
  scene.background = new Color("#0b0b0b");

  const renderer = new WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.setSize(container.clientWidth, container.clientHeight, false);
  renderer.outputEncoding = sRGBEncoding;
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = PCFSoftShadowMap;
  container.appendChild(renderer.domElement);

  const camera = new PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.01, 2000);
  camera.position.set(6, 6, 6);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.target.set(0, 0, 0);

  const hemi = new HemisphereLight(0xffffff, 0x444444, 0.6);
  scene.add(hemi);
  const dir = new DirectionalLight(0xffffff, 1.0);
  dir.position.set(5, 10, 7);
  dir.castShadow = true;
  dir.shadow.mapSize.set(1024, 1024);
  scene.add(dir);
  const amb = new AmbientLight(0xffffff, 0.2);
  scene.add(amb);

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
    if (!payload || typeof payload !== "object") throw new Error("loadUrdfFromPayload(payload): invalid payload.");
    const opts = defaultOptions(payload.options || {});

    camera.up.set(0, opts.upAxis === "z" ? 0 : 1, opts.upAxis === "z" ? 1 : 0);

    const meshUrlMap = {};
    for (const [name, b64] of Object.entries(payload.meshes || {})) {
      meshUrlMap[name] = b64ToBlobUrl(b64, "model/stl");
    }

    const urdfText = rewriteUrdfMeshFilenames(payload.urdf || "", meshUrlMap);
    const urdfBlob = new Blob([urdfText], { type: "text/xml" });
    const urdfUrl = URL.createObjectURL(urdfBlob);

    const stlLoader = new STLLoader();

    const urdfLoader = new URDFLoader();
    urdfLoader.loadMeshCb = function (path, manager, onComplete) {
      if (/\.stl(\?.*)?$/i.test(path)) {
        stlLoader.load(path, geometry => onComplete(geometry));
      } else {
        console.warn("Unsupported mesh type for path:", path);
        onComplete(null);
      }
    };

    if (robot) { scene.remove(robot); robot = null; }

    const dist = Math.max(0.1, Number(opts.initialDistance) || 6.0);
    camera.position.set(dist, dist, dist);

    await new Promise((resolve, reject) => {
      urdfLoader.load(
        urdfUrl,
        (urdf) => {
          robot = urdf;
          if (opts.upAxis !== "z") robot.rotation.x = -Math.PI / 2;

          if (opts.castShadows) {
            robot.traverse(obj => {
              if (obj && 'castShadow' in obj) obj.castShadow = true;
              if (obj && 'receiveShadow' in obj) obj.receiveShadow = true;
            });
          }

          controls.target.set(0, 0, 0);
          controls.update();

          scene.add(robot);
          resolve();
        },
        undefined,
        (err) => reject(err)
      );
    });

    setBackground(opts.background || "#0b0b0b");
    setGrid(!!opts.showGrid);
    console.log("[Viewer] URDF loaded. Meshes:", Object.keys(payload.meshes || {}).length);
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
