import sympy
import gdown
import cascadio
import trimesh
import base64
from IPython.display import display,HTML

#__all__ = ['StepRender']
def Download_Step(Drive_Link,Output_Name):
    url = f"https://drive.google.com/uc?id={Drive_Link}"
    output_Step = Output_Name+".step"
    gdown.download(url, output_Step, quiet=True)

def Step_Render(Step_Name):
    # function body
    #pass
    #file_id = Drive_Link
    #url = f"https://drive.google.com/uc?id={file_id}"
    
    output_Step = Step_Name+".step"
    output_glb = Step_Name+".glb"
    output_glb_scaled = Step_Name+"_scaled"+".glb"
    #gdown.download(url, output_Step, quiet=True)

    # Convert STEP to GLB
    glb_base64 = cascadio.step_to_glb(output_Step, output_glb)
    display(type(glb_base64))

    # Load and scale the mesh
    mesh = trimesh.load(output_glb)
    display(type(mesh))
        
    TARGET_SIZE = 2  # Set your desired mesh size
    current_size = max(mesh.extents)
    scale_factor = TARGET_SIZE / current_size
    mesh.apply_scale(scale_factor)
    mesh.export(output_glb_scaled)
    
    # Properly encode the final GLB as base64
    with open(output_glb_scaled, "rb") as glb_file:
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

    from IPython.display import HTML

    html_name = output_Step + "_scaled" + ".html"

    # Save HTML file (write mode)
    with open(html_name, "w") as f:
        f.write(html_content)  # Make sure you're writing the actual HTML content here

    # If you really need to read it back (though this is usually unnecessary)
    with open(html_name, "r") as f:
        html = f.read()
    
    display(HTML(html))


#with open("Sketch_3D_Viewer.html", "r") as f:
#    html_content = f.read()
