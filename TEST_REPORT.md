# ClipPilot AI — Comprehensive Automated Test Report

**Evaluation Date:** Current Session  
**Test Suite Target:** IncuBrix Selection PS2 (Prompt-Based Video Editing Engine)  
**Host Environment:** Windows (NT 10.0.26200), Python 3.10.11, Node.js 22.17.1, FFmpeg 9.0.1 Essentials  
**Overall Result:** **24 PASSED / 0 FAILED (100% Pass Rate)**

---

## 1. Test Execution Breakdown

| Test File | Test Case | Scope & Description | Result |
|---|---|---|---|
| `test_prompt_parser.py` | `test_trim_start_variations` | Verifies variations: "Remove first 5s", "Cut first 5s", "Trim opening 5s", "Discard first 5 sec" | **PASSED** |
| `test_prompt_parser.py` | `test_keep_first_vs_remove_first` | Semantic distinction: "Remove first 3s" (trim) vs "Keep first 3s" (slice 0..3) | **PASSED** |
| `test_prompt_parser.py` | `test_trim_end` | "Cut the last 4 seconds" | **PASSED** |
| `test_prompt_parser.py` | `test_time_slice_intervals` | Intervals: "Keep from 0:02 to 0:08", "Extract between 3 and 10 seconds", "Slice from 00:01 to 00:05" | **PASSED** |
| `test_prompt_parser.py` | `test_aspect_ratios` | Aspect ratios: 9:16 portrait vertical (TikTok/Reel), 1:1 square (Instagram), 16:9 widescreen landscape | **PASSED** |
| `test_prompt_parser.py` | `test_audio_adjustments` | Mute audio, volume scaling (50%, 200%), percentage parsing | **PASSED** |
| `test_prompt_parser.py` | `test_silence_and_subtitles` | Silence detection request and subtitle burning generation | **PASSED** |
| `test_prompt_parser.py` | `test_invalid_range_detection` | Detects start >= end ("Keep from 0:10 to 0:02") and warns user | **PASSED** |
| `test_prompt_parser.py` | `test_out_of_bounds_trim` | Detects trim > total media duration (e.g. trim 20s from 15s video) | **PASSED** |
| `test_prompt_parser.py` | `test_prompt_injection_safety` | Blocks malicious command chaining (`; rm -rf /; DROP TABLE jobs;`) | **PASSED** |
| `test_prompt_parser.py` | `test_unsupported_operation_repair` | Handles unsupported tasks (e.g. face swap) and offers valid nearest repair suggestion | **PASSED** |
| `test_security.py` | `test_prompt_injection_command_chaining` | Tests shell command injection prevention across multiple operators (`&&`, `;`, `\|`) | **PASSED** |
| `test_security.py` | `test_windows_subtitle_path_escaping` | Tests FFmpeg filter path sanitization (escaping Windows drive colon `C\:` and slashes) | **PASSED** |
| `test_security.py` | `test_upload_path_traversal_rejection` | Tests path traversal upload rejection (`../../../../etc/passwd.mp4`) | **PASSED** |
| `test_video_processor.py`| `test_media_inspector` | Verifies real FFprobe extraction: duration, dimensions, fps, codec, audio presence | **PASSED** |
| `test_video_processor.py`| `test_silence_detection` | Verifies FFmpeg `silencedetect` on synthetic talking head (detects 3.0s pause) | **PASSED** |
| `test_video_processor.py`| `test_trim_and_vertical_aspect` | Real transcode: trims 3s, crops to 1080x1920 (9:16 vertical), verifies output decodability | **PASSED** |
| `test_video_processor.py`| `test_square_aspect_and_resolution` | Real transcode: crops to 1:1 square at 720x720, verifies dimensions | **PASSED** |
| `test_video_processor.py`| `test_silent_video_processing` | Verifies video without audio track processes cleanly without filter crash | **PASSED** |
| `test_video_processor.py`| `test_subtitle_burning` | Real transcode: generates timestamped SRT and burns subtitles cleanly into MP4 | **PASSED** |
| `test_api_jobs.py` | `test_health_endpoint` | `GET /api/health` returns status: "ok", service: "ClipPilot AI" | **PASSED** |
| `test_api_jobs.py` | `test_capabilities_endpoint` | `GET /api/capabilities` returns real FFmpeg 9.0 version & 10 operations | **PASSED** |
| `test_api_jobs.py` | `test_1_click_demo_lifecycle` | End-to-end API lifecycle: demo creation, plan approval, queue, execution, preview, download, receipt | **PASSED** |
| `test_api_jobs.py` | `test_upload_invalid_extension` | Validates rejection of disallowed executable extensions (`malicious.exe`) | **PASSED** |

---

## 2. Live End-to-End System Verification (`scripts/verify_e2e.py`)

All 9 end-to-end acceptance stages executed and verified against live running HTTP services:

1. **Backend Health Probe:** Verified `HTTP 200 OK` on `http://127.0.0.1:8000/api/health`
2. **System Capabilities Probe:** Verified `HTTP 200 OK`, FFmpeg 9.0.1 Essentials, and 10 operations
3. **Frontend Web Server:** Verified `HTTP 200 OK` on `http://127.0.0.1:5173`
4. **1-Click Demo Creation:** Verified instant demo job with bundled synthetic talking-head video
5. **Plan Approval:** Verified transition to `queued`
6. **Processing Pipeline:** Verified state machine `queued` -> `processing` (30%) -> `completed` (100%) in **1.53s**
7. **Media Decodability:** Verified `preview/output` stream returned 2,257,701 bytes of valid MP4 video
8. **Cryptographic Edit Receipt:** Verified receipt JSON with 4 applied operations, time audit, and input/output dimensions
9. **SQLite Persistence:** Verified job metadata persisted in SQLite database

---

## 3. How to Reproduce Test Results

From the workspace root:

```powershell
# 1. Run full Pytest backend suite (24 tests)
cd d:\incubrix\backend
python -m pytest tests -v

# 2. Run live End-to-End verification script
cd d:\incubrix
python scripts\verify_e2e.py
```
