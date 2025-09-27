# filepath: braw-to-mp4-resolve/scripts/resolve_batch_braw_to_mp4.py
# Batch convert .braw to .mp4 using DaVinci Resolve's Python API (Windows-friendly)
#
# Usage (from Resolve menu or external):
#   python resolve_batch_braw_to_mp4.py --src "G:\\My Drive\\Medical Tech\\BRAW" --out "G:\\My Drive\\Medical Tech\\MP4" --project "MedicalTech_BRAW_to_MP4"
#
# Notes:
# - Best run from DaVinci Resolve's Workspace > Scripts menu (no extra setup).
# - If run externally, ensure PYTHONPATH includes Resolve's Scripting\Modules folder; see README for steps.
# - Renders "Individual Clips" so each .braw becomes its own .mp4 using the clip's name.
# - Existing .mp4 outputs are skipped to allow resuming.

import argparse
import os
import sys
import time
from datetime import datetime
from typing import Optional

LOG_PREFIX = "[BRAW->MP4]"


def _print(msg: str):
    print(f"{LOG_PREFIX} {msg}")


def _find_resolve_module_paths():
    paths = []
    env_path = os.environ.get("RESOLVE_SCRIPT_API")
    if env_path:
        paths.append(env_path)
    programdata = os.environ.get("PROGRAMDATA", r"C:\\ProgramData")
    paths.append(os.path.join(programdata, r"Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"))
    programfiles = os.environ.get("PROGRAMFILES", r"C:\\Program Files")
    paths.append(os.path.join(programfiles, r"Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"))
    return [p for p in paths if p]


def _get_bmd_and_resolve():
    try:
        import DaVinciResolveScript as bmd  # type: ignore
    except ImportError:
        for p in _find_resolve_module_paths():
            if os.path.isdir(p) and p not in sys.path:
                sys.path.append(p)
        try:
            import DaVinciResolveScript as bmd  # type: ignore
        except ImportError as e:
            _print("Unable to import DaVinciResolveScript. Run this from Resolve's script menu or set PYTHONPATH to the Modules folder.")
            raise e

    resolve = bmd.scriptapp("Resolve")
    if not resolve:
        raise RuntimeError("Could not acquire Resolve scripting instance. Make sure Resolve is running, or run the script from Resolve's menu.")
    return bmd, resolve


def _validate_paths(src: str, out: str):
    if not os.path.isdir(src):
        raise FileNotFoundError(f"Source folder not found: {src}")
    os.makedirs(out, exist_ok=True)


def _list_braw_files(src: str):
    exts = {".braw"}
    files = []
    for name in os.listdir(src):
        p = os.path.join(src, name)
        if os.path.isfile(p) and os.path.splitext(name)[1].lower() in exts:
            files.append(p)
    files.sort()
    return files


def _existing_outputs_map(out_dir: str):
    existing = set()
    for name in os.listdir(out_dir):
        if name.lower().endswith(".mp4"):
            base = os.path.splitext(name)[0].lower()
            existing.add(base)
    return existing


def _clip_basename_from_path(p: str) -> str:
    return os.path.splitext(os.path.basename(p))[0]


def _skip_already_rendered(files, out_dir):
    existing = _existing_outputs_map(out_dir)
    keep = []
    for f in files:
        base = _clip_basename_from_path(f).lower()
        if base in existing:
            _print(f"Skip (already exists): {base}.mp4")
        else:
            keep.append(f)
    return keep


def _configure_project_for_render(project, out_dir: str, fps: Optional[float], width: Optional[int], height: Optional[int]):
    try:
        presets = project.GetRenderPresetsList() or []
        for preferred in ("H.264 Master", "YouTube", "H264 Master", "MP4 H.264"):
            if preferred in presets:
                project.LoadRenderPreset(preferred)
                break
    except Exception:
        pass

    settings = {
        "TargetDir": out_dir,
        "ExportVideo": True,
        "ExportAudio": True,
        "Format": "mp4",
        "VideoCodec": "H.264",
        "Quality": "Automatic",
        "AudioCodec": "AAC",
        "AudioBitRate": 192000,
        "UseUniqueFilenames": True,
    }

    if width and height:
        settings["ResolutionWidth"] = int(width)
        settings["ResolutionHeight"] = int(height)

    project.SetRenderSettings(settings)

    if fps:
        try:
            project.SetSetting("timelineFrameRate", str(fps))
            project.SetSetting("timelinePlaybackFrameRate", str(fps))
        except Exception:
            pass

    try:
        project.SetRenderMode("IndividualClips")
    except Exception:
        pass


def _render_and_wait(project, job_id=None):
    ok = False
    if job_id:
        ok = project.StartRendering(job_id)
    else:
        ok = project.StartRendering()
    if not ok:
        raise RuntimeError("Failed to start rendering.")

    while project.IsRenderingInProgress():
        try:
            jobs = project.GetRenderJobs() or []
            if jobs:
                last = jobs[-1]
                st = project.GetRenderJobStatus(last["JobId"]) if isinstance(last, dict) else None
                if st and "CompletionPercentage" in st:
                    _print(f"Rendering... {st['CompletionPercentage']}%")
        except Exception:
            pass
        time.sleep(2)

    try:
        project.DeleteAllRenderJobs()
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser(description="Batch convert .braw to .mp4 via DaVinci Resolve API")
    ap.add_argument("--src", required=True, help="Folder containing .braw files")
    ap.add_argument("--out", required=True, help="Output folder for .mp4 files (Google Drive path works)")
    ap.add_argument("--project", default="BRAW_to_MP4_Auto", help="Resolve project name to create/use")
    ap.add_argument("--fps", type=float, default=None, help="Optional timeline FPS (e.g., 24, 25, 29.97)")
    ap.add_argument("--width", type=int, default=None, help="Optional output width (default = source/project)")
    ap.add_argument("--height", type=int, default=None, help="Optional output height (default = source/project)")
    ap.add_argument("--dry", action="store_true", help="List what would render and exit")
    args = ap.parse_args()

    src = os.path.abspath(args.src)
    out = os.path.abspath(args.out)

    _validate_paths(src, out)

    braw_files = _list_braw_files(src)
    if not braw_files:
        _print(f"No .braw files found in: {src}")
        return 0

    to_render = _skip_already_rendered(braw_files, out)
    if not to_render:
        _print("All files already rendered. Nothing to do.")
        return 0

    _print(f"Files to render: {len(to_render)}/{len(braw_files)}")
    if args.dry:
        for f in to_render:
            _print(f"Would render: {os.path.basename(f)}")
        return 0

    bmd, resolve = _get_bmd_and_resolve()

    pm = resolve.GetProjectManager()
    project = pm.LoadProject(args.project)
    if not project:
        project = pm.CreateProject(args.project)
    if not project:
        raise RuntimeError("Could not create or open the Resolve project.")

    _print(f"Using project: {args.project}")

    mediapool = project.GetMediaPool()
    if not mediapool:
        raise RuntimeError("Failed to access Media Pool.")

    media_storage = bmd.scriptapp("MediaStorage")

    _print("Importing clips to Media Pool...")
    added_items = media_storage.AddItemListToMediaPool(to_render)
    if not added_items:
        raise RuntimeError("Failed to import media to Media Pool.")

    tl_name = f"BRAW Batch {datetime.now().strftime('%Y%m%d_%H%M%S')}"
    _print(f"Creating timeline: {tl_name}")
    timeline = mediapool.CreateTimelineFromClips(tl_name, added_items)
    if not timeline:
        timeline = mediapool.CreateEmptyTimeline(tl_name)
        if not timeline:
            raise RuntimeError("Failed to create a timeline.")
        mediapool.AppendToTimeline(added_items)

    project.SetCurrentTimeline(timeline)

    _configure_project_for_render(project, out, args.fps, args.width, args.height)

    _print("Queuing render job...")
    job_id = project.AddRenderJob()
    if not job_id:
        raise RuntimeError("Failed to add render job.")

    _print("Starting render...")
    _render_and_wait(project, job_id)

    _print("Render complete. Files should be in: " + out)
    _print("If your output folder is in Google Drive, it will sync/upload automatically.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        _print(f"ERROR: {e}")
        sys.exit(1)