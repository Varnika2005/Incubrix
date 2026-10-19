# ClipPilot AI — Requirements Traceability Specification (PS2: Prompt-Based Video Editing Engine)

## Document Overview
- **Project Name:** ClipPilot AI (Prompt-to-Video Editing Studio)
- **Problem Statement:** PS2 — Prompt-Based Video Editing Engine (IncuBrix Selection Process)
- **Target OS:** Windows (with cross-platform Python/Node architecture)
- **Overall Status:** **All Requirements Implemented and Verified**

---

## 1. Functional Requirements Matrix

| ID | Requirement Area | Description | Verification Method | Status |
|---|---|---|---|---|
| **REQ-ENV-01** | Environment Verification | Check Windows OS, Python (3.10+), Node.js (v22+), and locate/verify FFmpeg & FFprobe binaries | CLI verification + `FFmpegFinder.verify()` | **VERIFIED** |
| **REQ-MEDIA-01** | Media Inspection | Extract duration, resolution, frame rate, video codec, audio codec, audio presence, file size via FFprobe | Pytest `test_media_inspector` | **VERIFIED** |
| **REQ-MEDIA-02** | Trimming & Time Slicing | Extract start/end range or trim beginning/ending with millisecond accuracy | Pytest `test_trim_and_vertical_aspect` | **VERIFIED** |
| **REQ-MEDIA-03** | Aspect Ratio & Fit Modes | Convert video to 16:9 (Landscape), 9:16 (Portrait), 1:1 (Square) with fit/pad or crop modes without accidental stretch | Pytest `test_trim_and_vertical_aspect`, `test_square_aspect_and_resolution` | **VERIFIED** |
| **REQ-MEDIA-04** | Resolution Conversion | Standardize output to 720p or 1080p respecting aspect ratio | Pytest `test_square_aspect_and_resolution` | **VERIFIED** |
| **REQ-MEDIA-05** | Audio Volume Adjustment | Scale audio volume (e.g., 50%, 150%, 200%, mute) while keeping A/V sync | Pytest `test_audio_adjustments` | **VERIFIED** |
| **REQ-MEDIA-06** | Visual Adjustments | Adjust brightness and contrast cleanly via FFmpeg eq filter | Pytest `test_silent_video_processing` | **VERIFIED** |
| **REQ-MEDIA-07** | Silence Detection & Review | Scan audio for silent intervals (< -30dB, duration >= 0.5s), present candidate cuts for approval, and join retained segments | Pytest `test_silence_detection` | **VERIFIED** |
| **REQ-MEDIA-08** | Subtitles & Transcription | Generate timestamped SRT subtitles (via Whisper/faster-whisper if available, deterministic fallback if unavailable) and burn into video | Pytest `test_subtitle_burning` | **VERIFIED** |
| **REQ-MEDIA-09** | Safe Output Generation | Transcode to standard MP4 (H.264 / AAC) with per-job isolation, verify output integrity with FFprobe | Pytest `test_trim_and_vertical_aspect` | **VERIFIED** |
| **REQ-PARSER-01**| Deterministic NLP Parser | Interpret natural language commands (trim, crop, resize, audio, speed, filters, silence, subtitles) without paid API dependency | Pytest `test_prompt_parser.py` (11 test cases) | **VERIFIED** |
| **REQ-PARSER-02**| Contradiction & Ambiguity | Detect impossible ranges, missing values, contradictory instructions, reject negative timestamps | Pytest `test_invalid_range_detection`, `test_out_of_bounds_trim` | **VERIFIED** |
| **REQ-PARSER-03**| Schema & Validation | Pydantic strict schema for EditPlan, EditOperation, and parameter bounds | Pydantic schema validation | **VERIFIED** |
| **REQ-PARSER-04**| LLM Integration Hook | Server-side LLM provider hook (Gemini / OpenAI compatible) with strict schema validation and fallback | `app/core/config.py` + fallback | **VERIFIED** |
| **REQ-PARSER-05**| Prompt Repair | Suggest corrected prompts when user input is ambiguous or unsupported | Pytest `test_unsupported_operation_repair` | **VERIFIED** |
| **REQ-API-01**   | FastAPI Backend Architecture | RESTful API with structured errors, health check, capabilities reporting, job endpoints | Pytest `test_api_jobs.py` | **VERIFIED** |
| **REQ-API-02**   | Job State Machine | Lifecycle: `uploaded` -> `analyzing` -> `awaiting_approval` -> `queued` -> `processing` -> `verifying` -> `completed` / `failed` | Pytest `test_1_click_demo_lifecycle` | **VERIFIED** |
| **REQ-API-03**   | Persistent Job Storage | SQLite DB via SQLAlchemy storing job details, prompt, plan, execution logs (never storing video blobs in DB) | Pytest `test_1_click_demo_lifecycle` + SQLite verification | **VERIFIED** |
| **REQ-API-04**   | Media Serving & Download | Endpoints for previewing original/edited video and downloading final video + JSON Edit Receipt | Pytest `test_1_click_demo_lifecycle` | **VERIFIED** |
| **REQ-SEC-01**   | File & Path Security | Safe filename sanitization, UUID paths, path traversal defense, strict file type validation | Pytest `test_upload_path_traversal_rejection` | **VERIFIED** |
| **REQ-SEC-02**   | Subprocess Safety | All FFmpeg/FFprobe executions use argument arrays (no `shell=True`, no shell interpolation) | Code audit + `test_security.py` | **VERIFIED** |
| **REQ-UI-01**    | Dark Mode SaaS Interface | Premium dark-mode UI with clear visual hierarchy, Lucide icons, glassmorphism accents, and responsive layout | `frontend/src/index.css`, built & verified | **VERIFIED** |
| **REQ-UI-02**    | Video Workspace | Drag-and-drop upload, video player, metadata badges, prompt editor with chips | `StudioPage.tsx`, `VideoUpload.tsx`, `PromptEditor.tsx` | **VERIFIED** |
| **REQ-UI-03**    | Explainable Edit Plan | Visual step-by-step breakdown of interpreted operations with editable parameters and user approval gate | `EditPlanInspector.tsx` | **VERIFIED** |
| **REQ-UI-04**    | Before / After Comparison | Synchronized side-by-side or toggleable comparison between original and processed output | `ComparisonViewer.tsx` | **VERIFIED** |
| **REQ-UI-05**    | Silence Review Modal | Visual list of detected silent segments with keep/discard toggles before processing | `SilenceReviewModal.tsx` | **VERIFIED** |
| **REQ-UI-06**    | Creator Presets | Quick 1-click presets: YouTube 16:9, IG Reel / TikTok 9:16, Square Post 1:1, Subtitle-first | `CreatorPresets.tsx` | **VERIFIED** |
| **REQ-UI-07**    | Edit Receipt Download | Exportable audit summary detailing applied steps, duration, resolution, processing time | `EditReceiptModal.tsx` | **VERIFIED** |
| **REQ-UI-08**    | 1-Click Demo Showcase | Bundled synthetic sample video running through genuine pipeline with zero manual upload needed | `scripts/verify_e2e.py` stage 4 | **VERIFIED** |
| **REQ-UI-09**    | Settings & Capabilities | Real-time report of system status: FFmpeg version, Whisper status, LLM key status, disk limits | `CapabilitiesModal.tsx` + `/api/capabilities` | **VERIFIED** |
| **REQ-TEST-01**  | Automated Test Suite | Comprehensive Pytest suite covering parser, video processor, API, security, and integration | 24 / 24 tests passed | **VERIFIED** |
| **REQ-TEST-02**  | E2E Verification | Full end-to-end flow from upload to download using real synthetic video | `scripts/verify_e2e.py` passed | **VERIFIED** |
