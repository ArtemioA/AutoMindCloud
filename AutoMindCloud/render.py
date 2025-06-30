import sympy
import gdown
import cascadio
import trimesh
import base64

def Render(Drive_Link, Output_Name):
    file_id = Drive_Link
    url = f"https://drive.google.com/uc?id={file_id}"
    output = Output_Name+".step"
    #gdown.download(url, output, quiet=True)

    # Convert STEP to GLB
    cascadio.step_to_glb(Output_Name+".step", Output_Name+".glb")

    # Load and scale the mesh
    mesh = trimesh.load(Output_Name+".glb")
    TARGET_SIZE = 2  # Set your desired mesh size
    current_size = max(mesh.extents)
    scale_factor = TARGET_SIZE / current_size
    mesh.apply_scale(scale_factor)
    mesh.export(Output_Name+".glb")

    # Properly encode the final GLB as base64
    with open("Sketch_scaled.glb", "rb") as glb_file:
        glb_bytes = glb_file.read()
        glb_base64 = base64.b64encode(glb_bytes).decode("utf-8")

    # Step 3: Create the HTML viewer
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Sketch.glb 3D Viewer</title>
        <style>
            body {{ margin: 0; overflow: hidden; }}
            canvas {{ display: block; }}
        </style>
    </head>
    <body>
        <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/build/three.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/loaders/GLTFLoader.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/controls/OrbitControls.js"></script>
        <script>
            const scene = new THREE.Scene();
            scene.background = new THREE.Color(0xf0f0f0);

            const camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.01, 1000);
            camera.position.set(0, 0, 3);

            const renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            document.body.appendChild(renderer.domElement);

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
                const binary_string = window.atob(base64);
                const len = binary_string.length;
                const bytes = new Uint8Array(len);
                for (let i = 0; i < len; i++) {{
                    bytes[i] = binary_string.charCodeAt(i);
                }}
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
                        if (Array.isArray(node.material)) {{
                            node.material.forEach(mat => mat.side = THREE.DoubleSide);
                        }} else {{
                            node.material.side = THREE.DoubleSide;
                        }}
                    }}
                }});
                scene.add(model);

                // Center the model
                const box = new THREE.Box3().setFromObject(model);
                const center = box.getCenter(new THREE.Vector3());
                model.position.sub(center);
            }}, function (error) {{
                console.error('Error loading GLB:', error);
            }});

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

    # Save HTML file
    html_filename = "Sketch_3D_Viewer.html"
    with open(html_filename, "w") as f:
        f.write(html_content)

    return html_filename
