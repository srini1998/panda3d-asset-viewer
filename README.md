# 3D Asset Viewer

A general-purpose Panda3D model viewer: load any `.egg`/`.bam`/`.gltf`
model, orbit around it with the mouse, zoom, toggle wireframe, and cycle
through three lighting presets. Built to demonstrate the asset-pipeline
and rendering side of the job (loading models, framing a camera,
lighting rigs, render-mode toggles).

![Orbit demo](orbit_demo.gif)

## What it demonstrates

- **Asset loading & auto-framing**: uses `getTightBounds()` to compute a
  model's size and automatically scales it to a consistent viewing size,
  regardless of the source model's native units.
- **Camera math**: spherical-coordinate orbit camera (heading/pitch/radius
  → Cartesian position) driven by mouse drag deltas.
- **Lighting presets**: `studio` (neutral three-point-ish), `sunset`
  (warm directional + dim ambient), `single-point` (a single point light
  to show shadowing/falloff) — cycled at runtime with **L**.
- **Render modes**: wireframe toggle via `setRenderModeWireframe()` /
  `setRenderModeFilled()`, useful for talking about how a mesh is
  actually built.

## Run it

```bash
pip install -r requirements.txt
python3 main.py                          # views models/smiley by default
python3 main.py --model models/frowney   # or point at your own asset
```

Controls: **left-drag** to orbit, **scroll** to zoom, **W** wireframe,
**L** cycle lighting.

## Headless / CI mode

```bash
python3 main.py --headless-demo
```

Renders a full 360° orbit as 24 PNG frames using an offscreen buffer (no
display needed), which is how `orbit_demo.gif` was generated:

```bash
python3 main.py --headless-demo
python3 - <<'EOF'
from PIL import Image
import glob
frames = sorted(glob.glob('frame_*.png'))
imgs = [Image.open(f).convert('RGB') for f in frames]
imgs[0].save('orbit_demo.gif', save_all=True, append_images=imgs[1:], duration=80, loop=0)
EOF
```

## Possible extensions

- Load `.gltf` assets via `panda3d-gltf` for modern art-pipeline exports.
- Add an on-screen polygon/vertex count readout.
- Support drag-and-drop model loading from the file system.
