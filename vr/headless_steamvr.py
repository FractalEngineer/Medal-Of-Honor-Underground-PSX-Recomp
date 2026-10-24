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

    def capture(self, destination, expected_pid, require_projection=True,
                reject_blank=True):
        """Collect new compositor backbuffer AND app-layer images, never old PNGs.

        reject_blank=False retains flat/black samples for temporal diagnosis
        instead of retrying until a nonblank frame hides a flicker.
        """
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
            changed_set = set(changed)
            pairs = []
            for backbuffer in changed:
                if backbuffer.stem.endswith(("-Layer", "-raw")):
                    continue
                # SteamVR versions differ: newer dumps use "-Layer", older
                # dumps expose the submitted projection as "-raw".
                for suffix in ("-Layer", "-raw"):
                    layer = backbuffer.with_name(backbuffer.stem + suffix + ".png")
                    if layer in changed_set:
                        pairs.append((backbuffer, layer))
                        break
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
                            if reject_blank and flat:
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
                        "blank_rejected": reject_blank,
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


def capture_series(compositor, destination, expected_pid, samples, interval,
                   reject_blank=True, require_clean=False):
    """Capture consecutive compositor/app-layer frames into one fresh tree."""
    if samples < 1:
        raise ValueError("samples must be at least 1")
    if interval < 0:
        raise ValueError("interval must be non-negative")
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    records = []
    for sample in range(samples):
        receipt = compositor.capture(
            destination / f"sample-{sample:03d}",
            expected_pid,
            require_projection=not reject_blank,
            reject_blank=reject_blank,
        )
        records.append({"sample": sample, "receipt": receipt})
        if sample + 1 < samples:
            time.sleep(interval)
    series = {
        "schema": 1,
        "interface": "IVRCompositor_029",
        "renderer_pid": expected_pid,
        "samples": records,
    }
    flat = [
        {"sample": record["sample"], "kind": image["kind"]}
        for record in records
        for image in record["receipt"]["images"]
        if image["flat"]
    ]
    series["clean"] = not flat
    (destination / "capture-series.json").write_text(
        json.dumps(series, indent=2) + "\n", encoding="utf-8"
    )
    if require_clean and flat:
        raise RuntimeError(f"Flat/black compositor frames detected: {flat}")
    return series


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--settings", type=Path)
    mode.add_argument("--capture", type=Path)
    parser.add_argument("--steamvr-root", type=Path)
    parser.add_argument("--pid", type=int)
    parser.add_argument("--samples", type=int, default=1)
    parser.add_argument("--interval", type=float, default=0.25)
    parser.add_argument("--allow-flat", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    args = parser.parse_args()
    if args.settings:
        print(null_settings(args.settings.read_text(encoding="utf-8-sig")), end="")
    else:
        if args.steamvr_root is None or args.pid is None:
            parser.error("--capture requires --steamvr-root and --pid")
        compositor = Compositor(args.steamvr_root)
        try:
            series = capture_series(
                compositor,
                args.capture,
                args.pid,
                args.samples,
                args.interval,
                # A cleanliness check must retain every sample; retrying a
                # blank frame would hide the flicker it is meant to detect.
                reject_blank=not (args.allow_flat or args.require_clean),
                require_clean=args.require_clean,
            )
        finally:
            compositor.close()
        print(json.dumps(series))
