// AutoMindCloud/URDFLoaderColab.js
// ES Module. Serve via jsDelivr, e.g.:
//   https://cdn.jsdelivr.net/gh/ArtemioA/AutoMindCloud/AutoMindCloud/URDFLoaderColab.js

// We keep versions known to work well together.
const IMPORT_MAP = {
  three: "https://cdn.jsdelivr.net/npm/three@0.127.0/build/three.module.js",
  controls: "https://cdn.jsdelivr.net/npm/three@0.127.0/examples/jsm/controls/OrbitControls.js",
  stlloader: "https://cdn.jsdelivr.net/npm/three@0.127.0/examples/jsm/loaders/STLLoader.js",
  urdf: "https://cdn.jsdelivr.net/npm/urdf-loader@0.10.1/src/URDFLoader.js"
};

async function loadModules() {
  const [{ Scene, PerspectiveCamera, WebGLRenderer, DirectionalLight, AmbientLight, PCFSoftShadowMap, Color, sRGBEncoding, ACESFilmicToneMapping, GridHelper, HemisphereLight, Vector3 },
         { OrbitControls },
         { STLLoader },
         { default: URDFLoader }] = await Promise.all([
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

/**
 * Rewrite <mesh filename="..."> in a URDF string to blob URLs using a mapping.
 * - mapping keys can be basenames or full paths
 */
function rewriteUrdfMeshFilenames(urdfText, mapping) {
  return urdfText.replace(/<mesh\s+filename="([^"]+)"/gi, (_, filename) => {
    const base = filename.split("/").pop();
    let url = mapping[filename] || mapping[base];
    if (!url) return `<mesh filename="${filename}"`;
    return `<mesh filename="${url}"`;
  });
}

function defaultOptions(user) {
  return {
    upAxis: "z",            // "z" or "y"
    initialDistance: 2.0,
    castShadows: true,
    background: "#0b0b0b",
    showGrid: true,
    ...user
  };
}

export default async function initViewer(container) {
  if (!container) throw new Error("initViewer(container): container is required.");
  const { Scene, PerspectiveCamera, WebGLRenderer, DirectionalLight, AmbientLight, PCFSoftShadowMap, Color, sRGBEncoding, ACESFilmicToneMapping, GridHelper, HemisphereLight, Vector3, OrbitControls, STLLoader, URDFLoader } = await loadModules();

  // Scene
  const scene = new Scene();
  scene.background = new Color("#0b0b0b");

  // Renderer
  const renderer = new WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.setSize(container.clientWidth, container.clientHeight, false);
  renderer.outputEncoding = sRGBEncoding;
  renderer.toneMapping = ACESFilmicToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = PCFSoftShadowMap;
  container.appendChild(renderer.domElement);

  // Camera
  const camera = new PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.01, 2000);
  camera.position.set(2, 2, 2);

  // Controls
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.target.set(0, 0, 0);

  // Lights
  const hemi = new HemisphereLight(0xffffff, 0x444444, 0.6);
  scene.add(hemi);
  const dir = new DirectionalLight(0xffffff, 1.0);
  dir.position.set(5, 10, 7);
  dir.castShadow = true;
  dir.shadow.mapSize.set(1024, 1024);
  scene.add(dir);
  const amb = new AmbientLight(0xffffff, 0.2);
  scene.add(amb);

  // Grid
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

  function setBackground(color) {
    scene.background = new Color(color);
  }
  function setGrid(visible) {
    grid.visible = !!visible;
  }
  function dispose() {
    renderer.dispose();
    container.removeChild(renderer.domElement);
  }

  // --- The main loader function you call from Colab ---
  async function loadUrdfFromPayload(payload) {
    if (!payload || typeof payload !== "object") throw new Error("loadUrdfFromPayload(payload): invalid payload.");
    const opts = defaultOptions(payload.options || {});

    // camera up axis
    if (opts.upAxis === "z") {
      // Make +Z up: rotate the camera target logic accordingly
      camera.up.set(0, 0, 1);
    } else {
      camera.up.set(0, 1, 0);
    }

    // Make blob URLs for each STL
    const meshUrlMap = {};
    for (const [name, b64] of Object.entries(payload.meshes || {})) {
      meshUrlMap[name] = b64ToBlobUrl(b64, "model/stl");
    }

    // Rewrite the URDF to point to blob URLs
    const urdfText = rewriteUrdfMeshFilenames(payload.urdf || "", meshUrlMap);

    // Build a Blob URL for the URDF file itself, so URDFLoader can "fetch" it
    const urdfBlob = new Blob([urdfText], { type: "text/xml" });
    const urdfUrl = URL.createObjectURL(urdfBlob);

    // Prepare URDFLoader + STL support
    const stlLoader = new STLLoader(); // STLLoader can read blob/object URLs via FileLoader internally

    const urdfLoader = new URDFLoader();
    // urdf-loader v0.10.1 uses internal loaders; we can set it like this:
    urdfLoader.loadMeshCb = function(path, manager, onComplete) {
      // Called for each mesh; detect STL by extension:
      if (/\.stl(\?.*)?$/i.test(path)) {
        stlLoader.load(path, geometry => {
          onComplete(geometry);
        });
      } else {
        console.warn("Unsupported mesh type for path:", path);
        onComplete(null);
      }
    };

    // Clear previous robot if any
    if (robot) {
      scene.remove(robot);
      robot = null;
    }

    // Kick camera back a little
    const dist = Math.max(0.1, Number(opts.initialDistance) || 2.0);
    camera.position.set(dist, dist, dist);

    // Load URDF
    await new Promise((resolve, reject) => {
      urdfLoader.load(
        urdfUrl,
        (urdf) => {
          robot = urdf;
          // Up-axis fix: many URDFs assume Z-up (ROS)
          if (opts.upAxis === "z") {
            // urdf-loader already orients according to URDF; we align scene/camera via camera.up and let it be.
          } else {
            // If Y-up desired, rotate robot so its Z aligns with Y:
            robot.rotation.x = -Math.PI / 2;
          }

          if (opts.castShadows) {
            robot.traverse(obj => {
              if (obj && 'castShadow' in obj) obj.castShadow = true;
              if (obj && 'receiveShadow' in obj) obj.receiveShadow = true;
            });
          }

          // Aim controls at the robot’s origin
          controls.target.set(0, 0, 0);
          controls.update();

          scene.add(robot);
          resolve();
        },
        undefined,
        (err) => reject(err)
      );
    });

    // Visual preferences
    setBackground(opts.background || "#0b0b0b");
    setGrid(!!opts.showGrid);
  }

  // Resize handling
  function onResize() {
    const w = container.clientWidth || window.innerWidth;
    const h = container.clientHeight || window.innerHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
  }
  window.addEventListener("resize", onResize);
  onResize();

  // Return a tiny API surface so callers can tweak things if needed
  return {
    scene, camera, renderer, controls,
    loadUrdfFromPayload,
    setBackground, setGrid,
    dispose
  };
}
