import base64, re, os, json
from IPython.display import HTML
import gdown, zipfile, shutil

def Download_URDF(Drive_Link, Output_Name="Model"):
    """
    Downloads a ZIP from Google Drive and extracts to /content/Output_Name
    """
    root_dir = "/content"
    file_id = Drive_Link.split('/d/')[1].split('/')[0]
    download_url = f'https://drive.google.com/uc?id={file_id}'
    zip_path = os.path.join(root_dir, Output_Name + ".zip")
    tmp_extract = os.path.join(root_dir, f"__tmp_extract_{Output_Name}")
    final_dir = os.path.join(root_dir, Output_Name)

    if os.path.exists(tmp_extract): shutil.rmtree(tmp_extract)
    os.makedirs(tmp_extract, exist_ok=True)
    if os.path.exists(final_dir): shutil.rmtree(final_dir)

    gdown.download(download_url, zip_path, quiet=True)

    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(tmp_extract)

    def is_junk(n): return n.startswith('.') or n == '__MACOSX'
    top = [n for n in os.listdir(tmp_extract) if not is_junk(n)]
    if len(top)==1 and os.path.isdir(os.path.join(tmp_extract, top[0])):
        shutil.move(os.path.join(tmp_extract, top[0]), final_dir)
    else:
        os.makedirs(final_dir, exist_ok=True)
        for n in top: shutil.move(os.path.join(tmp_extract, n), os.path.join(final_dir, n))

    shutil.rmtree(tmp_extract, ignore_errors=True)
    return final_dir

def URDF_Render(folder_path: str = "model"):
    # --- locate urdf/ and meshes/ (one level deep allowed) ---
    def find_dirs(root):
        d_u, d_m = os.path.join(root,"urdf"), os.path.join(root,"meshes")
        if os.path.isdir(d_u) and os.path.isdir(d_m): return d_u, d_m
        if os.path.isdir(root):
            for name in os.listdir(root):
                cand = os.path.join(root, name)
                u, m = os.path.join(cand,"urdf"), os.path.join(cand,"meshes")
                if os.path.isdir(u) and os.path.isdir(m): return u, m
        return None, None

    urdf_dir, meshes_dir = find_dirs(folder_path)
    if not urdf_dir or not meshes_dir:
        raise FileNotFoundError(f"Could not find urdf/ and meshes/ inside '{folder_path}' (or one nested level).")

    urdf_files = [f for f in os.listdir(urdf_dir) if f.lower().endswith(".urdf")]
    if not urdf_files:
        raise FileNotFoundError(f"No .urdf file in {urdf_dir}")
    urdf_path = os.path.join(urdf_dir, urdf_files[0])

    with open(urdf_path, "r", encoding="utf-8") as f:
        urdf_raw = f.read()

    def esc_js(s: str) -> str:
        return (s.replace('\\','\\\\').replace('`','\\`').replace('$','\\$').replace("</script>","<\\/script>"))

    # collect mesh refs
    mesh_refs = re.findall(r'filename="([^"]+\.(?:stl|dae))"', urdf_raw, re.IGNORECASE)
    mesh_refs = list(dict.fromkeys(mesh_refs))

    # index files on disk
    disk_files = []
    for root, _, files in os.walk(meshes_dir):
        for name in files:
            if name.lower().endswith((".stl",".dae",".png",".jpg",".jpeg")):
                disk_files.append(os.path.join(root, name))
    by_basename = {os.path.basename(p).lower(): p for p in disk_files}

    _cache = {}
    def b64(path):
        if path not in _cache:
            with open(path, "rb") as f:
                _cache[path] = base64.b64encode(f.read()).decode("ascii")
        return _cache[path]

    mesh_db = {}
    def add_entry(key, path):
        k = key.replace("\\","/").lower()
        if k not in mesh_db: mesh_db[k] = b64(path)

    # map URDF refs to files
    for ref in mesh_refs:
        base = os.path.basename(ref).lower()
        if base in by_basename:
            real = by_basename[base]
            add_entry(ref, real)
            add_entry(ref.replace("package://",""), real)
            add_entry(base, real)

    # include textures by basename
    for p in disk_files:
        bn = os.path.basename(p).lower()
        if bn.endswith((".png",".jpg",".jpeg")) and bn not in mesh_db:
            add_entry(bn, p)

    # === Full-screen HTML (only badge overlay) ===
    html = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>URDF Viewer</title>
<style>
  html,body { margin:0; height:100%; overflow:hidden; background:#f0f0f0; }
  canvas { display:block; width:100vw; height:100vh; }
  .badge{
      position:fixed;
      right:14px;
      bottom:12px;
      z-index:10;
      user-select:none;
      pointer-events:none;
  }
  .badge img{ max-height:40px; display:block; }
</style>
</head>
<body>
  <div class="badge">
    <img src="https://i.gyazo.com/30a9ecbd8f1a0483a7e07a10eaaa8522.png" alt="badge"/>
  </div>

<script src="https://cdn.jsdelivr.net/npm/three@0.132.2/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/controls/OrbitControls.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/loaders/STLLoader.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.132.2/examples/js/loaders/ColladaLoader.js"></script>
<script src="https://cdn.jsdelivr.net/npm/urdf-loader@0.12.6/umd/URDFLoader.js"></script>

<script>
(() => {
  // Clean previous viewer safely
  if (window.__URDF_VIEWER__ && typeof window.__URDF_VIEWER__.destroy === 'function') {
    try { window.__URDF_VIEWER__.destroy(); } catch(e){}
    try { delete window.__URDF_VIEWER__; } catch(e){}
  }

  const meshDB = /*__MESH_DB__*/ {};
  const urdfContent = `/*__URDF_CONTENT__*/`;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf0f0f0);

  const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.01, 10000);
  camera.position.set(0, 0, 3);

  const renderer = new THREE.WebGLRenderer({ antialias:true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.domElement.style.touchAction = 'none';
  document.body.appendChild(renderer.domElement);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;

  // lighting
  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const dirLight = new THREE.DirectionalLight(0xffffff, 1.0);
  dirLight.position.set(2, 2, 2);
  scene.add(dirLight);

  function onResize(){
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  }
  window.addEventListener('resize', onResize);

  // ---- URDF + mesh resolvers (scoped) ----
  const urdfLoader = new URDFLoader();
  const textDecoder = new TextDecoder();
  const b64ToUint8 = (b64) => Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const b64ToText  = (b64) => textDecoder.decode(b64ToUint8(b64));
  const MIME = { png:'image/png', jpg:'image/jpeg', jpeg:'image/jpeg', stl:'model/stl', dae:'model/vnd.collada+xml' };
  const normKey = s => String(s||'').replace(/\\/g,'/').toLowerCase();
  function variantsFor(path){
    const out = new Set(), p = normKey(path);
    out.add(p); out.add(p.replace(/^package:\/\//,''));
    const bn = p.split('/').pop();
    out.add(bn); out.add(bn.split('?')[0].split('#')[0]);
    const parts = p.split('/'); for (let i=1;i<parts.length;i++) out.add(parts.slice(i).join('/'));
    return Array.from(out);
  }

  const daeCache = new Map();
  let pendingMeshes = 0, fitTimer = null;

  function applyDoubleSided(obj){
    obj?.traverse?.(node=>{
      if (node.isMesh){
        if (Array.isArray(node.material)) node.material.forEach(m=>m.side=THREE.DoubleSide);
        else if (node.material) node.material.side = THREE.DoubleSide;
        node.castShadow = node.receiveShadow = true;
        node.geometry?.computeVertexNormals?.();
      }
    });
  }

  function scheduleFit(){
    if (fitTimer) clearTimeout(fitTimer);
    fitTimer = setTimeout(() => {
      if (pendingMeshes === 0 && api.robotModel) fitAndCenter(api.robotModel);
    }, 80);
  }

  // --- preserve good centering/fit behavior ---
  function fitAndCenter(object){
    const box = new THREE.Box3().setFromObject(object);
    if (box.isEmpty()) return;
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    const dist = maxDim * 1.8;               // same feel as previous version
    camera.near = Math.max(maxDim/1000, 0.001);
    camera.far  = Math.max(maxDim*1000, 1000);
    camera.updateProjectionMatrix();
    camera.position.copy(center.clone().add(new THREE.Vector3(dist, dist*0.9, dist)));
    controls.target.copy(center); controls.update();
  }

  urdfLoader.loadMeshCb = (path, manager, onComplete) => {
    const tries = variantsFor(path);
    let keyFound = null;
    for (const k of tries){ const kk = normKey(k); if (meshDB[kk]) { keyFound = kk; break; } }
    if (!keyFound){ onComplete(new THREE.Mesh()); return; }

    pendingMeshes++;
    const done = (mesh) => {
      applyDoubleSided(mesh);
      onComplete(mesh);
      pendingMeshes--; scheduleFit();
    };

    const ext = keyFound.split('.').pop();
    try{
      if (ext === 'stl'){
        const bytes = b64ToUint8(meshDB[keyFound]);
        const loader = new THREE.STLLoader();
        const geom = loader.parse(bytes.buffer);
        geom.computeVertexNormals();
        done(new THREE.Mesh(
          geom,
          new THREE.MeshStandardMaterial({ color: 0x8aa1ff, roughness: 0.85, metalness: 0.15, side: THREE.DoubleSide })
        ));
        return;
      }
      if (ext === 'dae'){
        if (daeCache.has(keyFound)){ done(daeCache.get(keyFound).clone(true)); return; }
        const daeText = b64ToText(meshDB[keyFound]);
        const mgr = new THREE.LoadingManager();
        mgr.setURLModifier((url)=>{
          const tries2 = variantsFor(url);
          for (const k2 of tries2){
            const key2 = normKey(k2);
            if (meshDB[key2]){
              const mime = MIME[key2.split('.').pop()] || 'application/octet-stream';
              return `data:${mime};base64,${meshDB[key2]}`;
            }
          }
          return url;
        });
        const loader = new THREE.ColladaLoader(mgr);
        const collada = loader.parse(daeText, '');
        const obj = collada.scene || new THREE.Object3D();
        daeCache.set(keyFound, obj);
        done(obj.clone(true));
        return;
      }
      done(new THREE.Mesh());
    }catch(e){ done(new THREE.Mesh()); }
  };

  // ---- Hover highlight + joint drag ----
  const api = { scene, camera, renderer, controls, robotModel:null, linkSet:null, linkToJoint:null };
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  function buildLinkMaps(robot){
    api.linkSet = new Set(Object.values(robot.links || {}));
    api.linkToJoint = new Map();
    Object.values(robot.joints || {}).forEach(j=>{
      let childLink = null;
      if ('child' in j && robot.links && robot.links[j.child]) childLink = robot.links[j.child];
      else for (const c of j.children) if (api.linkSet.has(c)) { childLink = c; break; }
      if (childLink) api.linkToJoint.set(childLink, j);
    });
  }

  const hoverState = { link:null, overlays:[] };
  function clearHover(){ hoverState.overlays.forEach(o=>{ o.parent&&o.parent.remove(o);}); hoverState.overlays.length=0; hoverState.link=null; }
  function showHover(link){
    if (hoverState.link===link) return;
    clearHover(); hoverState.link=link;
    link.traverse(o=>{
      if (o.isMesh && !o.userData.__hoverOverlay){
        const overlay = new THREE.Mesh(o.geometry, new THREE.MeshBasicMaterial({ color:0x9e9e9e, transparent:true, opacity:0.35, depthTest:false, depthWrite:false }));
        overlay.renderOrder=999; overlay.scale.set(1.03,1.03,1.03); overlay.userData.__hoverOverlay=true;
        o.add(overlay); hoverState.overlays.push(overlay);
      }
    });
  }

  let dragState = null, currentHoverJoint = null;

  function getPointer(e){
    const r = renderer.domElement.getBoundingClientRect();
    pointer.x = ((e.clientX - r.left)/r.width)*2-1;
    pointer.y = -((e.clientY - r.top)/r.height)*2+1;
  }

  function clampByLimits(val, joint, type){
    const lim = joint.limit || joint.limits || {};
    if (type !== 'continuous'){
      if (typeof lim.lower === 'number') val = Math.max(val, lim.lower);
      if (typeof lim.upper === 'number') val = Math.min(val, lim.upper);
    }
    return val;
  }

  function applyJointValue(joint, type, val){
    val = clampByLimits(val, joint, type);
    if (api.robotModel?.setJointValue && joint.name) api.robotModel.setJointValue(joint.name, val);
    else if (joint.setJointValue) joint.setJointValue(val);
    else { if (type==='prismatic') joint.position=val; else joint.angle=val; }
    api.robotModel?.updateMatrixWorld(true);
  }

  function startJointDrag(joint, ev){
    const type = joint.jointType || joint.type || 'revolute';
    const originW = joint.getWorldPosition(new THREE.Vector3());
    const qWorld = joint.getWorldQuaternion(new THREE.Quaternion());
    const axisW  = (joint.axis || new THREE.Vector3(1,0,0)).clone().normalize().applyQuaternion(qWorld).normalize();
    const startVal = (type==='prismatic') ? (joint.position||0) : (joint.angle||0);

    let rotPlane = null, r0 = null;
    if (type !== 'prismatic'){
      rotPlane = new THREE.Plane().setFromNormalAndCoplanarPoint(axisW, originW);
      raycaster.setFromCamera(pointer, camera);
      const p0 = new THREE.Vector3();
      const ok = raycaster.ray.intersectPlane(rotPlane, p0);
      r0 = ok ? p0.clone().sub(originW) : null;
      if (!r0 || r0.lengthSq()<1e-12){
        r0 = new THREE.Vector3().crossVectors(axisW, new THREE.Vector3(1,0,0));
        if (r0.lengthSq()<1e-8) r0 = new THREE.Vector3().crossVectors(axisW, new THREE.Vector3(0,1,0));
      }
      r0.normalize();
    }

    dragState = { joint, type, originW, axisW, rotPlane, r0, value:startVal };
    controls.enabled = false;
    renderer.domElement.style.cursor = 'grabbing';
    renderer.domElement.setPointerCapture?.(ev.pointerId);
  }

  function updateJointDrag(ev){
    const { joint, type, originW, axisW } = dragState;
    const fine = ev.shiftKey ? 0.35 : 1.0;

    if (type === 'prismatic'){
      const plane = new THREE.Plane().setFromNormalAndCoplanarPoint(axisW, originW);
      raycaster.setFromCamera(pointer, camera);
      const p = new THREE.Vector3();
      raycaster.ray.intersectPlane(plane, p);
      const t1 = p.clone().sub(originW).dot(axisW);
      const delta = (t1 - (dragState.lastT ?? t1)) * fine;
      dragState.value += delta; dragState.lastT = t1;
      applyJointValue(joint, type, dragState.value);
      return;
    }

    raycaster.setFromCamera(pointer, camera);
    const p = new THREE.Vector3();
    const hit = raycaster.ray.intersectPlane(dragState.rotPlane, p);
    if (!hit){
      const deltaRad = (ev.movementX||0) * 0.01 * fine;
      dragState.value += deltaRad; applyJointValue(joint, type, dragState.value);
      return;
    }
    let r1 = p.clone().sub(originW);
    if (r1.lengthSq()<1e-12) return;
    r1.normalize();

    const cross = new THREE.Vector3().crossVectors(dragState.r0, r1);
    const dot = THREE.Math.clamp(dragState.r0.dot(r1), -1, 1);
    const sign = Math.sign(axisW.dot(cross)) || 1;
    const delta = Math.atan2(cross.length(), dot) * sign * fine;

    dragState.value += delta; dragState.r0 = r1;
    applyJointValue(joint, type, dragState.value);
  }

  function endJointDrag(ev){
    if (dragState){
      renderer.domElement.releasePointerCapture?.(ev.pointerId);
      dragState = null;
    }
    controls.enabled = true;
    renderer.domElement.style.cursor = 'auto';
  }

  renderer.domElement.addEventListener('pointermove', (e)=>{
    getPointer(e);

    if (!dragState && api.robotModel){
      raycaster.setFromCamera(pointer, camera);
      const meshes=[]; api.robotModel.traverse(o=>{ if(o.isMesh && !o.userData.__hoverOverlay) meshes.push(o);});
      const hits = raycaster.intersectObjects(meshes,true);

      let hoverLink=null, hoverJoint=null;
      if (hits.length){
        const findAncestor=(o)=>{while(o){if(api.linkSet && api.linkSet.has(o))return o;o=o.parent;}return null;};
        const link = findAncestor(hits[0].object);
        if (link && api.linkToJoint && api.linkToJoint.has(link)){
          const j = api.linkToJoint.get(link);
          if (j && (j.jointType||j.type)!=='fixed'){ hoverLink=link; hoverJoint=j; }
        }
      }
      if (hoverLink){ showHover(hoverLink); renderer.domElement.style.cursor='grab'; currentHoverJoint=hoverJoint; }
      else { clearHover(); renderer.domElement.style.cursor='auto'; currentHoverJoint=null; }
    }

    if (dragState) updateJointDrag(e);
  }, {passive:true});

  renderer.domElement.addEventListener('pointerdown', (e)=>{
    e.preventDefault();
    if (!api.robotModel) return;
    getPointer(e);
    if (e.button!==0) return;
    if (currentHoverJoint && (currentHoverJoint.jointType||currentHoverJoint.type)!=='fixed'){
      startJointDrag(currentHoverJoint, e);
    }
  }, {passive:false});

  renderer.domElement.addEventListener('pointerup', endJointDrag);
  renderer.domElement.addEventListener('pointerleave', endJointDrag);
  renderer.domElement.addEventListener('pointercancel', endJointDrag);

  function buildLinkMapsAndFit(){
    buildLinkMaps(api.robotModel);
    scheduleFit();
  }

  function loadURDF(){
    if (api.robotModel) { scene.remove(api.robotModel); api.robotModel=null; }
    pendingMeshes = 0;
    try{
      const robot = urdfLoader.parse(urdfContent);
      if (robot?.isObject3D){
        api.robotModel = robot; scene.add(api.robotModel);
        setTimeout(buildLinkMapsAndFit, 30);
      }
    }catch(e){}
  }

  function animate(){ api._raf = requestAnimationFrame(animate); controls.update(); renderer.render(scene,camera); }
  animate();
  loadURDF();

  // expose a destroy for next runs
  api.destroy = function(){
    try{ cancelAnimationFrame(api._raf); }catch(e){}
    try{ window.removeEventListener('resize', onResize); }catch(e){}
    try{ if (api.robotModel) scene.remove(api.robotModel); }catch(e){}
    try{ renderer.dispose(); }catch(e){}
    try{ const el = renderer.domElement; el && el.parentNode && el.parentNode.removeChild(el); }catch(e){}
  };

  window.__URDF_VIEWER__ = api;
})(); // end IIFE
</script>
</body>
</html>"""

    html = html.replace("/*__MESH_DB__*/ {}", json.dumps(mesh_db))
    html = html.replace("/*__URDF_CONTENT__*/", esc_js(urdf_raw))
    return HTML(html)

