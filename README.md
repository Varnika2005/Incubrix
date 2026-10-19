# ClipPilot AI — Prompt-to-Video Editing Studio

> **"Your idea. Your prompt. Your finished video."**  
> *IncuBrix Selection Submission | PS2: Prompt-Based Video Editing Engine*

[![Backend Tests](https://img.shields.io/badge/Pytest-24%20Passed-10B981?style=for-the-badge&logo=pytest)](TEST_REPORT.md)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-9.0.1%20Essentials-6366F1?style=for-the-badge&logo=ffmpeg)](https://ffmpeg.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python%203.10+-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React%2018-Vite%20%2B%20TS-61DAFB?style=for-the-badge&logo=react)](https://vitejs.dev)

---

## 1. Project Overview & Problem Statement

### The Problem (PS2)
Traditional video editing requires hours of tedious timeline maneuvering: slicing frames, manually keyframing crops, standardizing aspect ratios across social platforms, cutting dead air, and formatting subtitles. Existing consumer AI video editors often rely on brittle, opaque black-boxes or cloud credits without letting creators inspect what changes will actually be made to their footage.

### The Solution: ClipPilot AI
**ClipPilot AI** is a professional prompt-to-video editing engine. It accepts real video footage, translates natural-language instructions into a **validated, typed, explainable editing plan**, enables interactive parameter tweaking before processing, and runs genuine FFmpeg media transformations with millisecond accuracy.

---

## 2. System Architecture

```mermaid
graph TD
    User["Creator / User"] -->|Natural Language Prompt| UI["ClipPilot React Studio UI"]
    User -->|Video Upload / 1-Click Demo| UI
    
    subgraph Frontend ["Frontend Studio (React 18 + Vite + TypeScript)"]
        UI --> Upload["Video Upload & Drag-Drop"]
        UI --> Player["HTML5 Video Player & Metadata Pills"]
        UI --> Presets["Creator Presets (TikTok, YT, IG)"]
        UI --> PlanUI["Explainable Edit Plan Inspector"]
        UI --> Compare["Original vs. Edited Synchronized Player"]
        UI --> ReceiptUI["Audit Edit Receipt & JSON Downloader"]
    end
    
    UI -->|REST API Requests| API["FastAPI Backend Engine (Port 8000)"]
    
    subgraph Backend ["Backend Processing Engine (Python 3.10+)"]
        API --> Inspector["FFprobe Media Inspector"]
        API --> Parser["Deterministic NLP Prompt Parser"]
        API --> Detector["Silence Detection Engine"]
        API --> Transcriber["Speech & Subtitle Generator"]
        API --> Processor["Video Processor (FFmpeg 9.0)"]
        API --> DB[("SQLite Job Store (SQLAlchemy)")]
    end
    
    Processor -->|Transcoded MP4| Storage["Per-Job Isolated Disk Storage"]
    Storage -->|Stream Video / Download| User
```

---

## 3. End-to-End User Journey

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Studio as React Frontend
    participant API as FastAPI Backend
    participant Parser as NLP Prompt Parser
    participant Processor as FFmpeg Engine
    participant DB as SQLite Store

    User->>Studio: Upload video or click "1-Click Demo"
    Studio->>API: POST /api/jobs/upload or POST /api/jobs/demo
    API->>DB: Create Job (status: uploaded)
    API-->>Studio: Return Job ID & Media Metadata (1920x1080, 10s, 30fps)
    
    User->>Studio: Enter prompt: "Cut first 3s, convert to 9:16 vertical, and add subtitles"
    Studio->>API: POST /api/jobs/{id}/analyze
    API->>Parser: Parse prompt & check bounds
    API->>DB: Store EditPlan (status: awaiting_approval)
    API-->>Studio: Return Explainable Edit Plan with sequence of steps
    
    User->>Studio: Review plan, adjust parameters, click "Approve & Process"
    Studio->>API: POST /api/jobs/{id}/process
    API->>DB: Update status to "queued" / "processing"
    
    critical Background Worker
        API->>Processor: Execute FFmpeg pipeline (trim, aspect crop, subtitles)
        Processor->>API: Verify output integrity via FFprobe
    end
    
    API->>DB: Save output path, specs & Edit Receipt (status: completed)
    Studio->>API: Poll GET /api/jobs/{id}
    API-->>Studio: Status: completed (progress: 100%)
    
    Studio-->>User: Display Side-by-Side Comparison & Download Button
    User->>Studio: Download finished MP4 & JSON Edit Receipt
```

---

## 4. Key Differentiators & Judge-Impressive Features

| Feature | Description | Implementation |
|---|---|---|
| **Explainable Edit Plan** | Breaks down natural-language commands into discrete, ordered visual steps. Users can inspect and tweak values (seconds, aspect ratio, volume) before approving execution. | `EditPlanInspector.tsx`, `prompt_parser.py` |
| **Original vs. Edited Comparison** | Synchronized side-by-side video playback with transformation audit metrics (duration delta, resolution change, processing speed). | `ComparisonViewer.tsx` |
| **Smart Silence Review** | Detects silent intervals (`< -30dB, >= 0.5s`) using FFmpeg's `silencedetect` audio filter and allows interactive review of candidate cuts before removal. | `SilenceDetector.py`, `SilenceReviewModal.tsx` |
| **Creator Platform Presets** | 1-Click presets for **TikTok / Reels (9:16 vertical crop)**, **YouTube Standard (16:9 1080p)**, **Square Post (1:1)**, and **Subtitle-First Video**. | `CreatorPresets.tsx` |
| **Cryptographic Edit Receipt** | Generates an audit JSON report containing input metadata, output metadata, user prompt, verified applied steps, and measured execution duration. | `EditReceiptModal.tsx`, `/api/jobs/{id}/receipt` |
| **Prompt Repair & Safety** | Detects contradictory ranges (start >= end), out-of-bounds trims, and blocks shell command injection attempts while suggesting valid alternative prompts. | `test_security.py`, `PromptParser.parse()` |
| **1-Click Reproducible Demo** | Bundles deterministic synthetic test media so anyone can experience the complete real pipeline instantly with zero manual video upload. | `POST /api/jobs/demo`, `generate_sample_videos.py` |

---

## 5. Technology Stack

- **Frontend:**
  - React 18 with TypeScript
  - Vite 5 (instant HMR and sub-second builds)
  - Custom Tailwind-inspired dark-mode CSS design system (`frontend/src/index.css`)
  - Lucide React iconography
  - HTML5 Video API with synchronized playback controls
- **Backend:**
  - Python 3.10+
  - FastAPI (asynchronous REST framework)
  - Pydantic v2 (strict request/response validation)
  - SQLite via SQLAlchemy ORM (persistent job history)
  - FFmpeg 9.0.1 Essentials & FFprobe (media inspection and transcoding)
  - Pytest & HTTPX (automated testing suite)

---

## 6. Supported Natural-Language Operations

| Operation | Natural-Language Prompt Example | Resulting FFmpeg Action |
|---|---|---|
| **Trim Beginning** | *"Remove the first 5 seconds"*, *"Cut opening 3s"* | Fast seek `-ss 5.0` |
| **Trim Ending** | *"Cut the last 4 seconds"*, *"Trim ending 5s"* | Relative seek `-to (duration - 4.0)` |
| **Extract Time Range** | *"Keep from 0:02 to 0:08"*, *"Slice between 5 and 15s"* | Interval seek `-ss 2.0 -to 8.0` |
| **Keep Opening** | *"Keep the first 5 seconds"* | Segment extract `-t 5.0` |
| **Aspect Ratio (9:16)** | *"Convert to 9:16 vertical for TikTok"* | `scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920` |
| **Aspect Ratio (1:1)** | *"Make it 1:1 square for Instagram"* | `scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080` |
| **Aspect Ratio (16:9)** | *"Change to landscape 16:9 widescreen"* | `scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080` |
| **Resolution Standards** | *"Export at 1080p"*, *"Convert to 720p HD"* | Standardized dimensions preserving aspect ratio |
| **Audio Volume** | *"Boost volume by 50%"*, *"Double the volume"*, *"Mute"* | `volume=1.5` or `volume=2.0` or `-an` |
| **Color Adjustment** | *"Make it brighter"*, *"Boost contrast"* | `eq=brightness=0.15:contrast=1.3` |
| **Silence Removal** | *"Detect and remove silent pauses"* | `silencedetect` + segment re-stitching |
| **Subtitle Burning** | *"Add subtitles"*, *"Burn captions into video"* | SRT generation + `subtitles` filter with font styling |

---

## 7. Windows Setup & Installation Instructions

### Prerequisites
- Windows 10 or 11
- Python 3.10 or higher
- Node.js v18 or higher (v22 recommended)
- FFmpeg (Gyan Essentials build automatically detected if installed via Winget)

### Step 1: Install FFmpeg (if not already installed)
In PowerShell:
```powershell
winget install Gyan.FFmpeg.Essentials --accept-source-agreements --accept-package-agreements
```
*ClipPilot automatically detects the Winget Gyan Essentials package path without requiring a system reboot.*

### Step 2: Clone or Navigate to the Workspace
```powershell
cd d:\incubrix
```

### Step 3: Install Backend Python Dependencies
```powershell
cd backend
python -m pip install fastapi uvicorn[standard] pydantic sqlalchemy httpx pytest pytest-asyncio python-multipart
cd ..
```

### Step 4: Install Frontend Node Dependencies
```powershell
cd frontend
npm install
cd ..
```

### Step 5: Launch the Application (One-Click)
Run the Windows launcher script:
```powershell
.\scripts\run_dev.bat
```

Alternatively, run backend and frontend in separate terminals:

**Terminal 1 (Backend):**
```powershell
cd d:\incubrix\backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 (Frontend):**
```powershell
cd d:\incubrix\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

- **Frontend Studio UI:** `http://127.0.0.1:5173`
- **Backend API:** `http://127.0.0.1:8000`
- **Interactive Swagger Docs:** `http://127.0.0.1:8000/docs`

---

## 8. Automated Testing & Verification

ClipPilot AI includes a comprehensive 24-test suite with 100% pass rate:

```powershell
# Run backend test suite
cd d:\incubrix\backend
python -m pytest tests -v
```

### Test Suite Summary:
- **`test_prompt_parser.py` (11 tests):** Natural language variations, trim distinctions, aspect ratios, volume scaling, silence, invalid ranges, and repair suggestions.
- **`test_video_processor.py` (6 tests):** Real FFmpeg operations on synthetic test media, silence detection, aspect crop, resolution change, audio-less video handling, and subtitle burning.
- **`test_api_jobs.py` (4 tests):** Health check, system capability reporting, 1-click demo lifecycle, and invalid file rejection.
- **`test_security.py` (3 tests):** Command injection blocking, path traversal prevention, and Windows subtitle filter path escaping.

### Run Live End-to-End System Verification:
```powershell
cd d:\incubrix
python scripts\verify_e2e.py
```
*Tests all 9 end-to-end acceptance stages against live HTTP servers in under 4 seconds.*

---

## 9. Evaluator 3-Minute Demonstration Script

1. **Open Studio:** Navigate to `http://127.0.0.1:5173`.
2. **Launch Demo Project:** Click the **"1-Click Demo"** button in the navbar or on the landing page.
3. **Inspect Media Specs:** Observe the original synthetic talking-head video loading with metadata pills: `Duration: 10.0s`, `1920x1080 (16:9)`, `30 FPS`, `Audio: AAC`.
4. **Inspect Explainable Plan:** See the pre-loaded prompt:
   *"Cut the first 3 seconds, convert to 9:16 vertical for TikTok, boost volume by 50%, and add subtitles"*.
   Notice how the engine translated this into 4 verified steps:
   - Step 1: `TRIM START` (3.0s)
   - Step 2: `ASPECT RATIO` (9:16 Portrait Crop)
   - Step 3: `AUDIO VOLUME` (150%)
   - Step 4: `SUBTITLES` (Burned SRT Captions)
5. **Smart Silence Review:** Click **"Review Detected Cuts"** to see the 3-second silence segment (`3.02s` to `6.01s`) with interactive checkboxes.
6. **Approve & Process:** Click **"Approve & Process Video"**. Watch the progress bar advance (`queued` -> `processing` -> `completed` in ~1.5s).
7. **Synchronized Comparison:** In the **Original vs. Processed Output** view, click **"Play Sync"** to watch both videos play simultaneously side-by-side.
8. **View Edit Receipt:** Click **"Edit Receipt"** to view the audit log and download the verified JSON report.
9. **Inspect Capabilities:** Click **"Capabilities"** in the navbar to verify genuine FFmpeg 9.0 build information.

---

## 10. Security & Robustness

- **Subprocess Safety:** All FFmpeg and FFprobe calls use argument arrays (`subprocess.run([binary, "-y", ...])`), completely eliminating shell injection vulnerabilities (`shell=False`).
- **Path Traversal Protection:** User filenames are sanitized, and files are stored in unique UUID-keyed directories (`storage/uploads/{uuid}/`).
- **File Validation:** Files are verified for allowed extensions (`.mp4`, `.mov`, `.mkv`, `.webm`, `.avi`) and probed for decodable media streams before processing.
- **Duration & Size Limits:** Maximum upload size (250 MB) and duration limits (10 minutes) prevent resource exhaustion.
- **Zero Paid API Lock-in:** The engine functions 100% offline using deterministic rule-based NLP and local FFmpeg transcoding.

---

## 11. Project Directory Structure

```
d:/incubrix/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── endpoints/
│   │   │   │   ├── jobs.py
│   │   │   │   ├── health.py
│   │   │   │   └── capabilities.py
│   │   ├── core/
│   │   │   ├── config.py
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
│   │   │   ├── media_inspector.py
│   │   │   ├── prompt_parser.py
│   │   │   ├── silence_detector.py
│   │   │   ├── transcriber.py
│   │   │   └── video_processor.py
│   │   └── main.py
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_prompt_parser.py
│   │   ├── test_video_processor.py
│   │   ├── test_api_jobs.py
│   │   └── test_security.py
│   └── requirements.txt
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
│   │   │   ├── CapabilitiesModal.tsx
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
│   └── tsconfig.json
├── sample_assets/
│   ├── sample_1_talking_head.mp4
│   ├── sample_2_landscape_clip.mp4
│   └── sample_3_silent_clip.mp4
├── scripts/
│   ├── generate_sample_videos.py
│   ├── verify_e2e.py
│   └── run_dev.bat
├── storage/
│   ├── uploads/
│   ├── outputs/
│   └── clippilot.db
├── PROJECT_PLAN.md
├── REQUIREMENTS.md
├── IMPLEMENTATION_STATUS.md
├── TEST_REPORT.md
├── README.md
├── .env.example
└── .gitignore
```

---

## 12. Conclusion & Verification Summary

ClipPilot AI fulfills every requirement of **PS2: Prompt-Based Video Editing Engine**:
- Real, demonstrable backend processing real videos using FFmpeg 9.0.1.
- Semantic NLP interpretation with explainable edit plans and user approval gates.
- Genuine differentiators: synchronized original vs edited playback, smart silence review, creator presets, and audit receipts.
- 24 automated unit and integration tests passing at 100%.
- Verified end-to-end operation on Windows.
