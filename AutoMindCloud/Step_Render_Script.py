import sympy
import gdown
import cascadio
import trimesh
import base64
from IPython.display import display, HTML
import os

def Download_Step(Drive_Link, Output_Name):
    """
    Downloads a STEP file from Google Drive using the full Drive link.
    Saves it as Output_Name.step in /content.
    """
    root_dir = "/content"
    file_id = Drive_Link.split('/d/')[1].split('/')[0]  # Extract ID from full link
    url = f"https://drive.google.com/uc?id={file_id}"
    output_step = os.path.join(root_dir, Output_Name + ".step")
    gdown.download(url, output_step, quiet=True)

def Step_3D_Render(Step_Name):
    output_Step = Step_Name + ".step"
    output_glb = Step_Name + ".glb"
    output_glb_scaled = Step_Name + "_scaled.glb"

    # Convert STEP -> GLB
    _ = cascadio.step_to_glb(output_Step, output_glb)

    # Load and scale the mesh (uniformly to target bounding-box size)
    mesh = trimesh.load(output_glb)
    TARGET_SIZE = 2.0  # desired max dimension
    current_size = max(mesh.extents) if hasattr(mesh, "extents") else 1.0
    scale_factor = (TARGET_SIZE / current_size) if current_size else 1.0
    mesh.apply_scale(scale_factor)
    mesh.export(output_glb_scaled)

    # Base64 encode final GLB
    with open(output_glb_scaled, "rb") as glb_file:
        glb_base64 = base64.b64encode(glb_file.read()).decode("utf-8")

    # HTML viewer in a centered "box" (no borders/radius/shadow) + bottom-right image badge
    html_content = f"""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <title>{Step_Name} 3D Viewer</title>
      <style>
        :root {{ --bg:#f5f6fa; --card:#ffffff; }}
        html, body {{ height:100%; margin:0; background:var(--bg); font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial; }}
        #wrap {{ display:flex; align-items:center; justify-content:center; height:100%; padding:16px; box-sizing:border-box; }}
        /* Centered box, no custom borders/radius/shadow */
        #viewer {{ position:relative; width:min(1200px,95vw); height:min(80vh,820px); background:var(--card); overflow:hidden; }}
        .badge {{
          position:absolute; right:14px; bottom:12px; user-select:none; pointer-events:none;
        }}
        .badge img {{ max-height:40px; display:block; }}
        canvas {{ display:block; }}
      </style>
    </head>
    <body>
      <div id="wrap">
        <div id="viewer">
          <div class="badge">
            <img src="https://i.gyazo.com/30a9ecbd8f1a0483a7e07a10eaaa8522.png" alt="badge"/>
          </div>
        </div>
      </div>

      <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/build/three.min.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/loaders/GLTFLoader.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/controls/OrbitControls.js"></script>
      <script>
      (() => {{
        const container = document.getElementById('viewer');

        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf0f0f0);

        const camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.01, 10000);
        camera.position.set(0, 0, 3);

        const renderer = new THREE.WebGLRenderer({{ antialias: true }});
        renderer.setPixelRatio(window.devicePixelRatio || 1);
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.domElement.style.touchAction = 'none';
        container.appendChild(renderer.domElement);

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;

        // Lights
        scene.add(new THREE.AmbientLight(0xffffff, 0.7));
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.9);
        dirLight.position.set(2, 2, 2);
        scene.add(dirLight);

        // Resize to container
        function onResize() {{
          const w = container.clientWidth, h = container.clientHeight;
          camera.aspect = w / h;
          camera.updateProjectionMatrix();
          renderer.setSize(w, h);
        }}
        window.addEventListener('resize', onResize);

        // Load GLB from Base64
        function base64ToArrayBuffer(base64) {{
          const binary_string = window.atob(base64);
          const len = binary_string.length;
          const bytes = new Uint8Array(len);
          for (let i = 0; i < len; i++) bytes[i] = binary_string.charCodeAt(i);
          return bytes.buffer;
        }}

        const glbBase64 = "{glb_base64}";
        const arrayBuffer = base64ToArrayBuffer(glbBase64);

        const loader = new THREE.GLTFLoader();
        loader.parse(arrayBuffer, '', function (gltf) {{
          const model = gltf.scene;

          // Make materials double-sided
          model.traverse(function (node) {{
            if (node.isMesh && node.material) {{
              if (Array.isArray(node.material)) node.material.forEach(mat => mat.side = THREE.DoubleSide);
              else node.material.side = THREE.DoubleSide;
            }}
          }});
          scene.add(model);

          // Center & frame the model
          const box = new THREE.Box3().setFromObject(model);
          if (!box.isEmpty()) {{
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());
            model.position.sub(center);

            const maxDim = Math.max(size.x, size.y, size.z) || 1.0;
            const dist = maxDim * 1.8;
            camera.near = Math.max(maxDim / 1000, 0.001);
            camera.far  = Math.max(maxDim * 1000, 1000);
            camera.updateProjectionMatrix();
            camera.position.set(dist, dist * 0.6, dist);
            controls.target.set(0, 0, 0);
            controls.update();
          }}
        }}, function (error) {{
          console.error('Error loading GLB:', error);
        }});

        function animate() {{
          requestAnimationFrame(animate);
          controls.update();
          renderer.render(scene, camera);
        }}
        animate();
      }})();
      </script>
    </body>
    </html>
    """

    html_name = output_Step + "_scaled.html"

    # Save HTML file
    with open(html_name, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Display in notebook
    with open(html_name, "r", encoding="utf-8") as f:
        html = f.read()
    display(HTML(html))

# Example usage:
# Download_Step("https://drive.google.com/file/d/<FILE_ID>/view?usp=sharing", "StepModel")
# Step_3D_Render("StepModel")
