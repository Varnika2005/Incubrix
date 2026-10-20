import os
import subprocess
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
from app.services.ffmpeg_finder import FFmpegFinder
from app.core.config import SAMPLE_DIR

def generate_sample_videos():
    """
    Generates deterministic, synthetic test videos using FFmpeg testsrc and sine audio.
    Ensures zero reliance on external copyrighted footage.
    """
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = FFmpegFinder.get_ffmpeg_path()
    
    # 1. Sample 1: 10s 1920x1080 with intermittent audio (tone + silence intervals)
    # 0s-3s tone, 3s-6s silence, 6s-10s tone
    s1_path = SAMPLE_DIR / "sample_1_talking_head.mp4"
    if not s1_path.exists():
        print(f"Generating {s1_path.name}...")
        # Generates test video with testsrc2, a sine wave audio with a 3s volume drop (silence)
        cmd_s1 = [
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=30:duration=10",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=10",
            "-af", "volume=enable='between(t,3,6)':volume=0",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
            "-c:a", "aac", "-b:a", "128k",
            "-brand", "mp42", "-movflags", "+faststart",
            str(s1_path)
        ]
        res = subprocess.run(cmd_s1, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error creating s1: {res.stderr}")
        else:
            print(f"Created {s1_path.name} successfully.")
    else:
        print(f"{s1_path.name} already exists.")

    # 2. Sample 2: 15s 1280x720 30fps Landscape Video
    s2_path = SAMPLE_DIR / "sample_2_landscape_clip.mp4"
    if not s2_path.exists():
        print(f"Generating {s2_path.name}...")
        cmd_s2 = [
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", "smptebars=size=1280x720:rate=30:duration=15",
            "-f", "lavfi", "-i", "sine=frequency=880:duration=15",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
            "-c:a", "aac",
            "-brand", "mp42", "-movflags", "+faststart",
            str(s2_path)
        ]
        res = subprocess.run(cmd_s2, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error creating s2: {res.stderr}")
        else:
            print(f"Created {s2_path.name} successfully.")
    else:
        print(f"{s2_path.name} already exists.")

    # 3. Sample 3: 6s 1080x1080 Square Video with NO audio stream
    s3_path = SAMPLE_DIR / "sample_3_silent_clip.mp4"
    if not s3_path.exists():
        print(f"Generating {s3_path.name}...")
        cmd_s3 = [
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", "color=c=navy:size=1080x1080:rate=30:duration=6",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
            "-an",
            "-brand", "mp42", "-movflags", "+faststart",
            str(s3_path)
        ]
        res = subprocess.run(cmd_s3, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error creating s3: {res.stderr}")
        else:
            print(f"Created {s3_path.name} successfully.")
    else:
        print(f"{s3_path.name} already exists.")

if __name__ == "__main__":
    generate_sample_videos()
