import os
import shutil
import base64
import gdown
import trimesh
import cascadio
from IPython.display import display, HTML

# -----------------------
# Helpers for output dir
# -----------------------
def _stem(path: str) -> str:
    return os.path.splitext(os.path.basename(path))[0]

def derive_output_base(stl_path: str = None, zip_path: str = None, fallback: str = None) -> str:
    if stl_path and os.path.splitext(stl_path)[1].lower() == ".stl":
        return _stem(stl_path)
    if zip_path and os.path.splitext(zip_path)[1].lower() == ".zip":
        return _stem(zip_path)
    if fallback:
        return fallback
    raise ValueError("Cannot derive output base name. Provide stl_path, zip_path, or fallback.")

def ensure_output_dir(base_name: str, root_dir: str = "/content") -> str:
    out_dir = os.path.join(root_dir, base_name)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir

def copy_stl_into_folder(stl_path: str, out_dir: str):
    if stl_path and os.path.exists(stl_path):
        shutil.copy2(stl_path, os.path.join(out_dir, os.path.basename(stl_path)))

def _persist_glb(cascadio_result, output_glb: str):
    """
    Make sure output_glb exists on disk.
    cascadio_result may be:
      - None (function wrote to disk)
      - bytes (raw GLB)
      - str (base64 or path)
    """
    if os.path.exists(output_glb):
        return

    if cascadio_result is None:
        # Nothing returned; assume cascadio wrote to disk but maybe to a different path.
        # If still missing, it's an error.
        if not os.path.exists(output_glb):
            raise RuntimeError(f"GLB was not created at: {output_glb}")
        return

    if isinstance(cascadio_result, (bytes, bytearray)):
        with open(output_glb, "wb") as f:
            f.write(cascadio_result)
        return

    if isinstance(cascadio_result, str):
        # Try base64 first
        try:
            raw = base64.b64decode(cascadio_result, validate=True)
            with open(output_glb, "wb") as f:
                f.write(raw)
            return
        except Exception:
            # Not base64; maybe it's a path that cascadio created
            if os.path.exists(cascadio_result):
                # Copy to expected location
                shutil.copy2(cascadio_result, output_glb)
                return
            raise RuntimeError("cascadio.step_to_glb returned a string that is neither base64 nor an existing file path.")

    raise RuntimeError("Unexpected return from cascadio.step_to_glb; cannot persist GLB.")

# -----------------------
# Drive download (no prints/returns)
# -----------------------
def Download_Step(Drive_Link: str, Output_Name: str = None, stl_path: str = None, zip_path: str = None):
    root_dir = "/content"
    base = derive_output_base(stl_path=stl_path, zip_path=zip_path, fallback=Output_Name)
    out_dir = ensure_output_dir(base, root_dir=root_dir)

    file_id = Drive_Link.split('/d/')[1].split('/')[0]
    url = f"https://drive.google.com/uc?id={file_id}"

    output_step = os.path.join(out_dir, base + ".step")
    gdown.download(url, output_step, quiet=True)

    copy_stl_into_folder(stl_path, out_dir)

# -----------------------
# STEP -> GLB -> HTML viewer (no prints/returns)
# -----------------------
def Step_3D_Render(Step_Name: str, stl_path: str = None, zip_path: str = None, target_size: float = 2.0):
    root_dir = "/content"
    base = derive_output_base(stl_path=stl_path, zip_path=zip_path, fallback=Step_Name)
    out_dir = ensure_output_dir(base, root_dir=root_dir)

    output_step = os.path.join(out_dir, base + ".step")
    output_glb = os.path.join(out_dir, base + ".glb")
    output_glb_scaled = os.path.join(out_dir, base + "_scaled.glb")
    html_name = os.path.join(out_dir, base + "_viewer.html")

    # If user passed a direct path, honor it; else expect /content/<BASE>/<BASE>.step
    if os.path.isabs(Step_Name) or os.path.exists(Step_Name):
        output_step = Step_Name
    else:
        if not os.path.exists(output_step):
            raise FileNotFoundError(
                f"STEP not found at expected path: {output_step}. "
                f"Run Download_Step(...) first or pass a direct STEP path to Step_3D_Render."
            )

    copy_stl_into_folder(stl_path, out_dir)

    # Convert STEP -> GLB and ensure the file exists
    cascadio_result = cascadio.step_to_glb(output_step, output_glb)
    _persist_glb(cascadio_result, output_glb)
    if not os.path.exists(output_glb):
        raise RuntimeError(f"Failed to create GLB at: {output_glb}")

    # Load and scale
    mesh = trimesh.load(output_glb)
    current_size = float(max(mesh.extents)) if hasattr(mesh, "extents") else None
    if not current_size or current_size == 0:
        raise ValueError("Could not determine mesh size from GLB for scaling.")
    scale_factor = float(target_size) / current_size
    mesh.apply_scale(scale_factor)
    mesh.export(output_glb_scaled)

    # Inline viewer
    with open(output_glb_scaled, "rb") as f:
        glb_base64 = base64.b64encode(f.read()).decode("utf-8")

    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<title>{base} — 3D Viewer</title>
<style>
  html, body {{ margin:0; height:100%; overflow:hidden; background:#f0f0f0; }}
  #app {{ width:100%; height:100%; }}
  canvas {{ display:block; }}
</style>
</head>
<body>
<div id="app"></div>

<script src="https://cdn.jsdelivr.net/npm/three@0.132.2/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/loaders/GLTFLoader.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/controls/OrbitControls.js"></script>
<script>
const container = document.getElementById('app');

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xf0f0f0);

const camera = new THREE.PerspectiveCamera(60, window.innerWidth/window.innerHeight, 0.01, 1000);
camera.position.set(0, 0, 3);

const renderer = new THREE.WebGLRenderer({ antialias:true });
renderer.setSize(window.innerWidth, window.innerHeight);
container.appendChild(renderer.domElement);

const controls = new THREE.OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;

scene.add(new THREE.AmbientLight(0xffffff, 0.6));
const dirLight = new THREE.DirectionalLight(0xffffff, 1);
dirLight.position.set(2, 2, 2);
scene.add(dirLight);

function base64ToArrayBuffer(base64) {{
  const binary = atob(base64);
  const len = binary.length;
  const bytes = new Uint8Array(len);
  for (let i=0; i<len; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}}

const glbBase64 = "{glb_base64}";
const arrayBuffer = base64ToArrayBuffer(glbBase64);

const loader = new THREE.GLTFLoader();
loader.parse(arrayBuffer, '', (gltf) => {{
  const model = gltf.scene;
  model.traverse(n => {{
    if (n.isMesh && n.material) {{
      if (Array.isArray(n.material)) n.material.forEach(m => m.side = THREE.DoubleSide);
      else n.material.side = THREE.DoubleSide;
    }}
  }});
  scene.add(model);

  const box = new THREE.Box3().setFromObject(model);
  const center = box.getCenter(new THREE.Vector3());
  model.position.sub(center);
}}, (err) => console.error('Error parsing GLB:', err));

function animate() {{
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
}}
animate();

window.addEventListener('resize', () => {{
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
}});
</script>
</body>
</html>
"""
    with open(html_name, "w", encoding="utf-8") as f:
        f.write(html_content)

    display(HTML(html_content))

