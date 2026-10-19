import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

class FFmpegFinder:
    """
    Robust locator for ffmpeg and ffprobe executables.
    Searches:
    1. Explicit environment variables (FFMPEG_PATH, FFPROBE_PATH)
    2. System and User PATH
    3. WinGet default package installation directories
    4. Local project tools/ directory
    """

    _cached_ffmpeg: Optional[str] = None
    _cached_ffprobe: Optional[str] = None

    @classmethod
    def get_ffmpeg_path(cls) -> str:
        if cls._cached_ffmpeg and os.path.exists(cls._cached_ffmpeg):
            return cls._cached_ffmpeg

        # 1. Environment variable override
        env_ffmpeg = os.getenv("FFMPEG_PATH")
        if env_ffmpeg and os.path.exists(env_ffmpeg):
            cls._cached_ffmpeg = env_ffmpeg
            return env_ffmpeg

        # 2. PATH resolution
        which_ffmpeg = shutil.which("ffmpeg")
        if which_ffmpeg:
            cls._cached_ffmpeg = which_ffmpeg
            return which_ffmpeg

        # 3. Known WinGet Gyan Essentials directory pattern on Windows
        local_app_data = os.getenv("LOCALAPPDATA", "")
        if local_app_data:
            winget_pkgs = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
            if winget_pkgs.exists():
                for p in winget_pkgs.glob("**/ffmpeg.exe"):
                    if p.is_file():
                        cls._cached_ffmpeg = str(p)
                        return str(p)

        # 4. Workspace fallback tools directory
        workspace_ffmpeg = Path(__file__).resolve().parent.parent.parent.parent / "tools" / "ffmpeg" / "bin" / "ffmpeg.exe"
        if workspace_ffmpeg.exists():
            cls._cached_ffmpeg = str(workspace_ffmpeg)
            return str(workspace_ffmpeg)

        # Fallback to plain binary name
        return "ffmpeg"

    @classmethod
    def get_ffprobe_path(cls) -> str:
        if cls._cached_ffprobe and os.path.exists(cls._cached_ffprobe):
            return cls._cached_ffprobe

        env_ffprobe = os.getenv("FFPROBE_PATH")
        if env_ffprobe and os.path.exists(env_ffprobe):
            cls._cached_ffprobe = env_ffprobe
            return env_ffprobe

        which_ffprobe = shutil.which("ffprobe")
        if which_ffprobe:
            cls._cached_ffprobe = which_ffprobe
            return which_ffprobe

        local_app_data = os.getenv("LOCALAPPDATA", "")
        if local_app_data:
            winget_pkgs = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
            if winget_pkgs.exists():
                for p in winget_pkgs.glob("**/ffprobe.exe"):
                    if p.is_file():
                        cls._cached_ffprobe = str(p)
                        return str(p)

        workspace_ffprobe = Path(__file__).resolve().parent.parent.parent.parent / "tools" / "ffmpeg" / "bin" / "ffprobe.exe"
        if workspace_ffprobe.exists():
            cls._cached_ffprobe = str(workspace_ffprobe)
            return str(workspace_ffprobe)

        return "ffprobe"

    @classmethod
    def verify(cls) -> Tuple[bool, str, str]:
        """
        Verify that both binaries exist and are executable.
        Returns: (is_valid, ffmpeg_version_summary, ffprobe_version_summary)
        """
        ffmpeg_bin = cls.get_ffmpeg_path()
        ffprobe_bin = cls.get_ffprobe_path()

        ffmpeg_ver = "Unknown"
        ffprobe_ver = "Unknown"
        is_ok = False

        try:
            res_ffmpeg = subprocess.run([ffmpeg_bin, "-version"], capture_output=True, text=True, check=True, timeout=5)
            first_line = res_ffmpeg.stdout.splitlines()[0] if res_ffmpeg.stdout else "Available"
            ffmpeg_ver = first_line

            res_ffprobe = subprocess.run([ffprobe_bin, "-version"], capture_output=True, text=True, check=True, timeout=5)
            first_probe = res_ffprobe.stdout.splitlines()[0] if res_ffprobe.stdout else "Available"
            ffprobe_ver = first_probe

            is_ok = True
        except Exception as e:
            ffmpeg_ver = f"Error executing ffmpeg: {str(e)}"

        return is_ok, ffmpeg_ver, ffprobe_ver
