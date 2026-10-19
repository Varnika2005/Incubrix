# ClipPilot AI — Implementation & Architecture Plan

## 1. Project Overview & Target Architecture
**ClipPilot AI** is a prompt-to-video editing studio that interprets natural language instructions into a strictly typed, validated edit plan, allows user inspection and interactive tweaking, and executes the editing plan using FFmpeg.

### Architectural Components:
1. **Frontend (Client Application)**
   - **Framework:** React 18 / Vite with TypeScript
   - **Styling:** Modern Tailwind CSS with dark-mode aesthetic (charcoal/slate, deep purple/cyan accents, glassmorphic cards)
   - **Icons & Assets:** Lucide React icons
   - **Key Views:**
     - Landing Hero & Value Proposition
     - Studio Workspace (Upload, Video Preview, Metadata Display, Prompt Input with Chips, Edit Plan Review Modal, Before/After Comparison, Silence Cut Inspector)
     - Job History Drawer / Page (persisted jobs, status, re-download, replay)
     - Capability & System Health Inspector (FFmpeg, Whisper, LLM status, disk space)
     - 1-Click Interactive Demo (preloaded synthetic video to test instant pipeline)

2. **Backend (API & Core Engine)**
   - **Framework:** FastAPI with Python 3.10+
   - **Validation:** Pydantic v2 schemas for all requests, responses, and edit plan steps
   - **Persistence:** SQLite via SQLAlchemy ORM for job metadata, states, and execution logs
   - **Media Processing Engine (`app/services/video_processor.py`):**
     - FFprobe metadata extraction (duration, width, height, aspect ratio, fps, audio presence, audio channels, video codec, format)
     - Subprocess array execution with strict timeout and sanitization (no `shell=True`)
     - Operations: Trim start/end, slice interval, aspect ratio resize (16:9, 9:16, 1:1) with fit/pad/crop modes, resolution standardizer (720p, 1080p), audio volume adjustment, brightness & contrast adjustment, silence detection & removal, subtitle generation & burning
     - Verification step: FFprobe decodability and duration/dimension check on generated output
   - **Prompt Understanding Engine (`app/services/prompt_parser.py`):**
     - Hybrid engine: 100% deterministic rule/regex-based parser for offline guaranteed accuracy
     - Optional LLM integration hook (Gemini / OpenAI API compatible) with strict JSON schema validation and local fallback
     - Contradiction and out-of-bounds detector (e.g. start >= end, trim > duration)
     - Suggestion / Repair engine for ambiguous or partially unsupported prompts
   - **Transcription & Subtitles (`app/services/transcriber.py`):**
     - Whisper / faster-whisper support when installed
     - Built-in deterministic fallback generator with timestamped speech simulation if external model is not downloaded
     - SRT generator and libass/subtitles filter burner
   - **Silence Review Engine (`app/services/silence_detector.py`):**
     - FFmpeg `silencedetect` filter runner
     - Returns detected intervals `[start, end, duration]`
     - Allows selective removal of approved intervals and segment re-stitching
   - **Storage Abstraction (`app/core/storage.py`):**
     - Safe disk storage with UUID job directories
     - Path traversal prevention
     - Cleanup routines for temporary files and jobs

---

## 2. Implementation Stages & Roadmap

| Stage | Focus Area | Deliverables | Status |
|---|---|---|---|
| **Stage 1** | System & Environment Inspection | Confirm OS, Python, Node, FFmpeg/FFprobe binaries; initialize documentation | COMPLETED |
| **Stage 2** | Scaffold Project Structure | FastAPI backend structure, Vite+React frontend structure, dependencies | IN PROGRESS |
| **Stage 3** | Core Video Processor & Synthetic Media | Implement `video_processor.py`, `media_inspector.py`, synthetic test generator | PENDING |
| **Stage 4** | Prompt Parser & Validation Schema | Implement `prompt_parser.py`, Pydantic models, prompt repair logic | PENDING |
| **Stage 5** | FastAPI Backend & Job Lifecycle | Job endpoints, SQLite DB, background processing, preview/download streaming | PENDING |
| **Stage 6** | Silence Detection & Subtitle Burner | Implement silence analysis and subtitle generation/burning | PENDING |
| **Stage 7** | Frontend Studio UI & Workspaces | Landing page, Studio Editor, Plan Inspector, Comparison View, Presets, History | PENDING |
| **Stage 8** | Security, Edge Cases & Verification | Subprocess sanitization, upload size/type limits, path traversal checks | PENDING |
| **Stage 9** | Automated Testing & Quality Audit | Pytest suite (Parser, Video Processor, API, Security) & Playwright/Browser test | PENDING |
| **Stage 10**| Docs & Submission Package | Comprehensive README, architecture diagrams, user manual, demo script | PENDING |

---

## 3. Directory Layout
```
d:/incubrix/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints/
│   │   │   │   ├── jobs.py
│   │   │   │   ├── health.py
│   │   │   │   └── capabilities.py
│   │   │   └── api.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── storage.py
│   │   ├── database/
│   │   │   ├── session.py
│   │   │   └── models.py
│   │   ├── schemas/
│   │   │   ├── edit_plan.py
│   │   │   ├── job.py
│   │   │   └── capabilities.py
│   │   ├── services/
│   │   │   ├── ffmpeg_finder.py
│   │   │   ├── video_processor.py
│   │   │   ├── prompt_parser.py
│   │   │   ├── silence_detector.py
│   │   │   └── transcriber.py
│   │   └── main.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_prompt_parser.py
│   │   ├── test_video_processor.py
│   │   ├── test_api_jobs.py
│   │   └── test_security.py
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.tsx
│   │   │   ├── VideoUpload.tsx
│   │   │   ├── VideoPlayer.tsx
│   │   │   ├── PromptEditor.tsx
│   │   │   ├── EditPlanInspector.tsx
│   │   │   ├── ComparisonViewer.tsx
│   │   │   ├── SilenceReviewModal.tsx
│   │   │   ├── CreatorPresets.tsx
│   │   │   ├── JobHistory.tsx
│   │   │   ├── CapabilityBadge.tsx
│   │   │   └── EditReceiptModal.tsx
│   │   ├── pages/
│   │   │   ├── LandingPage.tsx
│   │   │   └── StudioPage.tsx
│   │   ├── services/
│   │   │   └── api.ts
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── storage/
│   ├── uploads/
│   ├── outputs/
│   └── temp/
├── sample_assets/
├── scripts/
│   ├── generate_sample_videos.py
│   └── run_dev.bat
├── PROJECT_PLAN.md
├── REQUIREMENTS.md
├── IMPLEMENTATION_STATUS.md
├── TEST_REPORT.md
└── README.md
```
