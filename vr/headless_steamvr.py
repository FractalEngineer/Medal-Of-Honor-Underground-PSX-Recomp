"""SteamVR null-HMD configuration and compositor image capture.

Uses Valve's installed OpenVR DLL, not a replacement runtime. FnTable offsets
are deliberately tied to IVRCompositor_029 from Valve's openvr_capi.h. Reject
other versions rather than guessing their ABI. No third-party Python binding.
"""
import ctypes
import json
from pathlib import Path
import shutil
import time


def null_settings(original):
    """Preserve unrelated settings; force null and prevent Home launch races."""
    settings = json.loads(original)
    if not isinstance(settings, dict):
        raise ValueError("SteamVR settings must be a JSON object")
    for section in ("steamvr", "driver_null", "power", "dashboard"):
        if not isinstance(settings.setdefault(section, {}), dict):
            raise ValueError(f"SteamVR {section} settings must be an object")
    settings["driver_null"]["enable"] = True
    # Keep both eye viewports inside the desktop backbuffer used for captures.
    settings["driver_null"].update(
        {"windowX": 0, "windowY": 0, "windowWidth": 1920, "windowHeight": 1080}
    )
    settings["steamvr"].update(
        {
            "forcedDriver": "null",
            "activateMultipleDrivers": False,
            "enableHomeApp": False,
            "startDashboardFromAppLaunch": False,
        }
    )
    settings["power"].update(
        {
            "turnOffScreensTimeout": 3600.0,
            "pauseCompositorOnStandby": False,
        }
    )
    settings["dashboard"]["enableDashboard"] = False
    return json.dumps(settings, indent=3) + "\n"


class Compositor:
    """Background client: never takes scene focus away from the game."""

    def __init__(self, runtime):
        if not hasattr(ctypes, "WinDLL"):
            raise RuntimeError("SteamVR compositor capture requires Windows")
        self.runtime = Path(runtime).resolve()
        self.dll = ctypes.WinDLL(str(self.runtime / "bin/win64/openvr_api.dll"))
        self.dll.VR_InitInternal2.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_char_p,
        ]
        self.dll.VR_InitInternal2.restype = ctypes.c_uint32
        self.dll.VR_GetGenericInterface.argtypes = [
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
        ]
        self.dll.VR_GetGenericInterface.restype = ctypes.c_void_p
        self.dll.VR_ShutdownInternal.argtypes = []
        self.dll.VR_ShutdownInternal.restype = None
        error = ctypes.c_int()
        self.dll.VR_InitInternal2(ctypes.byref(error), 3, None)
        if error.value:
            raise RuntimeError(f"OpenVR background initialization failed: {error.value}")
        try:
            table = self.dll.VR_GetGenericInterface(
                b"FnTable:IVRCompositor_029", ctypes.byref(error)
            )
            if error.value or not table:
                raise RuntimeError(f"IVRCompositor_029 unavailable: {error.value}")
            entries = ctypes.cast(table, ctypes.POINTER(ctypes.c_void_p))
            self.renderer_pid = ctypes.WINFUNCTYPE(ctypes.c_uint32)(entries[25])
            self.dump_images = ctypes.WINFUNCTYPE(None)(entries[30])
        except BaseException:
            self.dll.VR_ShutdownInternal()
            raise

    def close(self):
        self.dll.VR_ShutdownInternal()

    def capture(self, destination, expected_pid, require_projection=True):
        """Collect new compositor backbuffer AND app-layer images, never old PNGs."""
        from PIL import Image, ImageStat

        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=False)
        source = self.runtime / "screenshots"
        before = {
            p.name: (p.stat().st_mtime_ns, p.stat().st_size)
            for p in source.glob("*.png")
        }
        pid_before = self.renderer_pid()
        if pid_before != expected_pid:
            raise RuntimeError(
                f"Compositor renderer {pid_before} is not owned game {expected_pid}"
            )
        self.dump_images()
        rejected = []
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            changed = [
                p
                for p in source.glob("*.png")
                if before.get(p.name) != (p.stat().st_mtime_ns, p.stat().st_size)
            ]
            pairs = [
                (p, p.with_name(p.stem + suffix + ".png"))
                for p in changed
                if not p.stem.endswith(("-Layer", "-raw"))
                for suffix in ("-raw", "-Layer")
            ]
            for backbuffer, layer in pairs:
                if layer not in changed:
                    continue
                try:
                    records = []
                    for original, label in (
                        (backbuffer, "compositor"),
                        (layer, "application_layer"),
                    ):
                        target = destination / f"{label}.png"
                        with Image.open(original) as image:
                            rgb = image.convert("RGB")
                            rgb.load()
                            extrema = rgb.getextrema()
                            flat = max(hi - lo for lo, hi in extrema) < 8
                            if flat and (label == "compositor" or require_projection):
                                raise RuntimeError(f"Blank/flat {label} capture")
                            dimensions = rgb.size
                            mean = ImageStat.Stat(rgb).mean
                        shutil.copyfile(original, target)
                        records.append(
                            {
                                "kind": label,
                                "path": str(target),
                                "source": str(original),
                                "size": dimensions,
                                "mean_rgb": mean,
                                "flat": flat,
                            }
                        )
                    pid_after = self.renderer_pid()
                    if pid_after != expected_pid:
                        raise RuntimeError(
                            f"Compositor renderer changed to {pid_after}"
                        )
                    return {
                        "interface": "IVRCompositor_029",
                        "renderer_pid_before": pid_before,
                        "renderer_pid_after": pid_after,
                        "images": records,
                        "atomic_guest_pair": False,
                        "projection_required": require_projection,
                        "rejected_dumps": rejected,
                    }
                except RuntimeError as exc:
                    if not str(exc).startswith("Blank/flat") or len(rejected) >= 2:
                        raise
                    rejected.append({"source": str(backbuffer), "reason": str(exc)})
                    time.sleep(1.1)
                    before = {
                        p.name: (p.stat().st_mtime_ns, p.stat().st_size)
                        for p in source.glob("*.png")
                    }
                    if self.renderer_pid() != expected_pid:
                        raise RuntimeError("Compositor renderer changed before retry")
                    self.dump_images()
                    break
                except (OSError, SyntaxError):
                    pass
            time.sleep(0.15)
        raise TimeoutError("No fresh compositor backbuffer/application-layer PNG pair")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path, required=True)
    args = parser.parse_args()
    print(null_settings(args.settings.read_text(encoding="utf-8-sig")), end="")
