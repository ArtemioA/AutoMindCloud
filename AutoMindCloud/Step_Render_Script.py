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
    """Return filename without extension."""
    return os.path.splitext(os.path.basename(path))[0]

def derive_output_base(stl_path: str = None, zip_path: str = None, fallback: str = None) -> str:
    """
    Priority for base name:
    1) STL file stem (e.g., myPart.stl -> "myPart")
    2) ZIP file stem (e.g., myPart.zip -> "myPart")
    3) Fallback string (e.g., Step_Name)
    """
    if stl_path and os.path.splitext(stl_path)[1].lower() == ".stl":
        return _stem(stl_path)
    if zip_path and os.path.splitext(zip_path)[1].lower() == ".zip":
        return _stem(zip_path)
    if fallback:
        return fallback
    #raise ValueError("Cannot derive output base name. Provide stl_path, zip_path, or fallback.")

def ensure_output_dir(base_name: str, root_dir: str = "/content") -> str:
    out_dir = os.path.join(root_dir, base_name)
    os.makedirs(out_dir, exist_ok=True)
    return out_dir

def copy_stl_into_folder(stl_path: str, out_dir: str):
    """
    If an STL path is provided and exists, copy it into out_dir.
    Keeps original filename.
    """
    if stl_path and os.path.exists(stl_path):
        shutil.copy2(stl_path, os.path.join(out_dir, os.path.basename(stl_path)))

# -----------------------
# Drive download
# -----------------------
def Download_Step(Drive_Link: str, Output_Name: str = None, stl_path: str = None, zip_path: str = None):
    """
    Downloads a STEP file from Google Drive using the full Drive link.
    Saves under /content/<BASE>/<BASE>.step where BASE is taken from:
      - stl_path filename (preferred), else
      - zip_path filename, else
      - Output_Name (fallback)
    Also copies the .stl into that same folder if stl_path is provided.
    """
    root_dir = "/content"
    base = derive_output_base(stl_path=stl_path, zip_path=zip_path, fallback=Output_Name)
    out_dir = ensure_output_dir(base, root_dir=root_dir)

    # Extract Drive file id
    file_id = Drive_Link.split('/d/')[1].split('/')[0]
    url = f"https://drive.google.com/uc?id={file_id}"

    # Save STEP inside the folder, named <base>.step
    output_step = os.path.join(out_dir, base + ".step")
    gdown.download(url, output_step, quiet=True)

    # Put the STL inside the same folder if provided
    copy_stl_into_folder(stl_path, out_dir)

    return out_dir, output_step, base

# -----------------------
# STEP -> GLB -> HTML viewer
# -----------------------
def Step_3D_Render(Step_Name: str, stl_path: str = None, zip_path: str = None, target_size: float = 2.0):
    """
    Converts /content/<BASE>/<BASE>.step to GLB, scales, and writes an HTML viewer,
    keeping all artifacts in /content/<BASE>/ where BASE is derived from the STL (or ZIP) name.
    If Step_Name doesn't include a path, the function assumes the STEP is at:
      /content/<BASE>/<BASE>.step
    """
    root_dir = "/content"
    # Derive base from STL or ZIP; Step_Name is used as fallback when needed
    base = derive_output_base(stl_path=stl_path, zip_path=zip_path, fallback=Step_Name)
    out_dir = ensure_output_dir(base, root_dir=root_dir)

    # Expected file paths
    output_step = os.path.join(out_dir, base + ".step")
    output_glb = os.path.join(out_dir, base + ".glb")
    output_glb_scaled = os.path.join(out_dir, base + "_scaled.glb")
    html_name = os.path.join(out_dir, base + "_viewer.html")

    # If the .step is elsewhere or named differently, allow Step_Name as a direct path
    if os.path.isabs(Step_Name) or os.path.exists(Step_Name):
        output_step = Step_Name  # honor explicit path
    else:
        # make sure expected STEP exists; otherwise fail fast
        if not os.path.exists(output_step):
            raise FileNotFoundError(f"STEP not found: {output_step}\n"
                                    f"Hint: run Download_Step(...) or pass a direct STEP path to Step_3D_Render.")

    # Copy STL into folder if available
    copy_stl_into_folder(stl_path, out_dir)

    # Convert STEP to GLB (writes output_glb)
    _ = cascadio.step_to_glb(output_step, output_glb)

    # Load and scale the mesh
    mesh = trimesh.load(output_glb)
    current_size = float(max(mesh.extents)) if hasattr(mesh, "extents") else None
    if not current_size or current_size == 0:
        raise ValueError("Could not determine mesh size from GLB for scaling.")
    scale_factor = float(target_size) / current_size
    mesh.apply_scale(scale_factor)
    mesh.export(output_glb_scaled)

    # Base64 for inlined viewer
    with open(output_glb_scaled, "rb") as f:
        glb_base64 = base64.b64encode(f.read()).decode("utf-8")

    # HTML viewer
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

// Lights
scene.add(new THREE.AmbientLight(0xffffff, 0.6));
const dirLight = new THREE.DirectionalLight(0xffffff, 1);
dirLight.position.set(2, 2, 2);
scene.add(dirLight);

// Load GLB from Base64
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

  // Center the model
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

    # Show inline in notebooks
    display(HTML(html_content))

    #return {
    #    "folder": out_dir,
    #    "step": output_step,
    #    "glb": output_glb,
    #    "glb_scaled": output_glb_scaled,
    #    "html": html_name,
    #    "scale_factor": scale_factor
    #}

# -----------------------
# Usage examples
# -----------------------
# 1) If your ZIP is named "robot_part.zip" and contains "robot_part.stl",
#    and your STEP file is at a Drive link:
# out_dir, step_path, base = Download_Step(
#     Drive_Link="https://drive.google.com/file/d/XXXXXXXXXXXX/view?usp=sharing",
#     zip_path="/content/robot_part.zip"     # derives BASE="robot_part"
# )
# Step_3D_Render(base, zip_path="/content/robot_part.zip")

# 2) If you have the STL path:
# out_dir, step_path, base = Download_Step(
#     Drive_Link="https://drive.google.com/file/d/XXXXXXXXXXXX/view?usp=sharing",
#     stl_path="/content/myWheel.stl"        # derives BASE="myWheel"
# )
# Step_3D_Render(base, stl_path="/content/myWheel.stl")

# 3) If you only want to pass explicit STEP path and still group by STL name:
# Step_3D_Render("/content/myWheel/myWheel.step", stl_path="/content/myWheel/myWheel.stl")
