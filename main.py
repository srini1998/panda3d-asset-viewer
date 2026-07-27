"""
3D Asset Viewer - loads a model, lets you orbit around it with the mouse,
toggle wireframe mode, and cycle through lighting presets.

Controls (interactive mode):
    Left mouse drag : orbit camera
    Scroll wheel    : zoom in/out
    W               : toggle wireframe
    L               : cycle lighting presets
    ESC             : quit

Usage:
    python3 main.py                     # view the default model
    python3 main.py --model path/to/model.egg
    python3 main.py --headless-demo     # render an orbit sequence to PNGs
                                         # and stitch them into a GIF
"""
import sys
import math
import argparse

from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from direct.task import Task
from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    PointLight,
    Vec4,
    TextNode,
    loadPrcFileData,
)

LIGHT_PRESETS = ["studio", "sunset", "single-point"]


class AssetViewer(ShowBase):
    def __init__(self, model_path="models/smiley", headless=False):
        if headless:
            loadPrcFileData("", "window-type offscreen")
            loadPrcFileData("", "audio-library-name null")
        ShowBase.__init__(self)

        self.headless = headless
        self.wireframe = False
        self.light_index = 0
        self.light_nodes = []

        self.disableMouse()
        self.model = self.loader.loadModel(model_path)
        self.model.reparentTo(self.render)
        self.model.setPos(0, 0, 0)

        # normalize scale so different models frame similarly
        bounds = self.model.getTightBounds()
        if bounds:
            min_p, max_p = bounds
            size = (max_p - min_p)
            largest = max(size.x, size.y, size.z, 0.01)
            self.model.setScale(6.0 / largest)

        self.orbit_radius = 18
        self.orbit_heading = 0.0
        self.orbit_pitch = -20.0

        self._apply_lighting(LIGHT_PRESETS[self.light_index])
        self._update_camera()
        self._setup_hud()

        if not headless:
            self.taskMgr.add(self.mouse_orbit_task, "mouse-orbit-task")
            self.accept("w", self._toggle_wireframe)
            self.accept("l", self._cycle_lighting)
            self.accept("wheel_up", self._zoom, [-1.5])
            self.accept("wheel_down", self._zoom, [1.5])
            self._drag_active = False
            self.accept("mouse1", self._start_drag)
            self.accept("mouse1-up", self._end_drag)
            self._last_mouse = None

    def _setup_hud(self):
        self.hud = OnscreenText(
            text="Drag: orbit | Scroll: zoom | W: wireframe | L: lighting",
            pos=(0, -0.95),
            scale=0.05,
            fg=(1, 1, 1, 1),
            align=TextNode.ACenter,
            mayChange=True,
        )

    def _clear_lights(self):
        for np in self.light_nodes:
            self.render.clearLight(np)
            np.removeNode()
        self.light_nodes = []

    def _apply_lighting(self, preset):
        self._clear_lights()
        if preset == "studio":
            amb = AmbientLight("amb")
            amb.setColor(Vec4(0.4, 0.4, 0.4, 1))
            amb_np = self.render.attachNewNode(amb)
            self.render.setLight(amb_np)
            self.light_nodes.append(amb_np)

            key = DirectionalLight("key")
            key.setColor(Vec4(1, 1, 0.95, 1))
            key_np = self.render.attachNewNode(key)
            key_np.setHpr(30, -45, 0)
            self.render.setLight(key_np)
            self.light_nodes.append(key_np)

        elif preset == "sunset":
            amb = AmbientLight("amb")
            amb.setColor(Vec4(0.25, 0.15, 0.2, 1))
            amb_np = self.render.attachNewNode(amb)
            self.render.setLight(amb_np)
            self.light_nodes.append(amb_np)

            sun = DirectionalLight("sun")
            sun.setColor(Vec4(1.0, 0.55, 0.25, 1))
            sun_np = self.render.attachNewNode(sun)
            sun_np.setHpr(90, -10, 0)
            self.render.setLight(sun_np)
            self.light_nodes.append(sun_np)

        elif preset == "single-point":
            pt = PointLight("pt")
            pt.setColor(Vec4(0.9, 0.9, 1.0, 1))
            pt_np = self.render.attachNewNode(pt)
            pt_np.setPos(10, -10, 10)
            self.render.setLight(pt_np)
            self.light_nodes.append(pt_np)

    def _cycle_lighting(self):
        self.light_index = (self.light_index + 1) % len(LIGHT_PRESETS)
        self._apply_lighting(LIGHT_PRESETS[self.light_index])

    def _toggle_wireframe(self):
        self.wireframe = not self.wireframe
        if self.wireframe:
            self.render.setRenderModeWireframe()
        else:
            self.render.setRenderModeFilled()

    def _zoom(self, amount):
        self.orbit_radius = max(4, min(40, self.orbit_radius + amount))
        self._update_camera()

    def _start_drag(self):
        self._drag_active = True

    def _end_drag(self):
        self._drag_active = False
        self._last_mouse = None

    def _update_camera(self):
        h = math.radians(self.orbit_heading)
        p = math.radians(self.orbit_pitch)
        x = self.orbit_radius * math.cos(p) * math.sin(h)
        y = -self.orbit_radius * math.cos(p) * math.cos(h)
        z = self.orbit_radius * math.sin(p) * -1 + 4
        self.camera.setPos(x, y, z)
        self.camera.lookAt(0, 0, 2)

    def mouse_orbit_task(self, task):
        if self._drag_active and self.mouseWatcherNode.hasMouse():
            mpos = self.mouseWatcherNode.getMouse()
            if self._last_mouse is not None:
                dx = mpos.x - self._last_mouse[0]
                dy = mpos.y - self._last_mouse[1]
                self.orbit_heading -= dx * 120
                self.orbit_pitch = max(-80, min(80, self.orbit_pitch + dy * 120))
                self._update_camera()
            self._last_mouse = (mpos.x, mpos.y)
        return Task.cont

    # ------------------------------------------------------------------
    def run_headless_orbit_demo(self, frame_count=24, out_prefix="frame"):
        """Render a full 360-degree orbit as a sequence of PNGs, suitable
        for stitching into a GIF with e.g. Pillow or ImageMagick."""
        paths = []
        for i in range(frame_count):
            self.orbit_heading = (360.0 / frame_count) * i
            self._update_camera()
            self.graphicsEngine.renderFrame()
            path = f"{out_prefix}_{i:03d}.png"
            self.win.saveScreenshot(path)
            paths.append(path)
        print(f"Rendered {len(paths)} orbit frames.")
        return paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/smiley")
    parser.add_argument("--headless-demo", action="store_true")
    args = parser.parse_args()

    app = AssetViewer(model_path=args.model, headless=args.headless_demo)
    if args.headless_demo:
        app.run_headless_orbit_demo()
    else:
        app.run()


if __name__ == "__main__":
    main()
