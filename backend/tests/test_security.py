from pathlib import Path
from app.services.prompt_parser import PromptParser
from app.services.transcriber import Transcriber

def test_prompt_injection_command_chaining():
    prompts = [
        "Trim 5s && rm -rf /",
        "Cut 2s; format C:",
        "Make it vertical; DROP TABLE jobs;",
        "<script>alert(1)</script>"
    ]
    for p in prompts:
        plan = PromptParser.parse(p)
        assert len(plan.operations) == 0, f"Malicious prompt should produce 0 operations: {p}"
        assert any("Potentially unsafe" in w for w in plan.warnings)

def test_windows_subtitle_path_escaping():
    windows_path = r"C:\Users\John Doe\AppData\Local\Temp\sub.srt"
    escaped = Transcriber.escape_path_for_ffmpeg(windows_path)
    # Must escape drive colon: C\:
    assert r"C\:" in escaped
    # Must convert backslashes to forward slashes
    assert "\\" not in escaped[3:]
    assert "C\\:/Users/John Doe/AppData/Local/Temp/sub.srt" == escaped

def test_upload_path_traversal_rejection(client):
    res = client.post(
        "/api/jobs/upload",
        files={"file": ("../../../../etc/passwd.mp4", b"corrupt media content", "video/mp4")}
    )
    # Either rejected for corruption or safely sanitized without traversal
    assert res.status_code in [400, 422]
