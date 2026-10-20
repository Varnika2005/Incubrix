# ClipPilot AI — Sources, Dependencies & Third-Party Attributions

This document provides a comprehensive inventory of all third-party software, libraries, frameworks, tools, models, and assets utilized in the development and execution of **ClipPilot AI**, along with their respective licenses, versions, sources, and integration purpose.

---

## 1. Backend Core & API Framework (Python Ecosystem)

| Library / Tool | Version | License | Source / Repository | Purpose & Role |
|---|---|---|---|---|
| **Python** | 3.10+ / 3.11 | PSF License | [python.org](https://www.python.org/) | Core backend runtime environment |
| **FastAPI** | 0.115.0+ | MIT | [github.com/fastapi/fastapi](https://github.com/fastapi/fastapi) | High-performance ASGI REST API framework, dependency injection, and OpenAPI generation |
| **Uvicorn** | 0.30.0+ | BSD-3-Clause | [github.com/encode/uvicorn](https://github.com/encode/uvicorn) | Asynchronous ASGI HTTP production web server |
| **Pydantic** | 2.9.0+ | MIT | [github.com/pydantic/pydantic](https://github.com/pydantic/pydantic) | Strict data validation, schema enforcement, and type coercion |
| **Pydantic-Settings** | 2.5.0+ | MIT | [github.com/pydantic/pydantic-settings](https://github.com/pydantic/pydantic-settings) | Centralized, type-safe environment variable management |
| **SQLAlchemy** | 2.0.35+ | MIT | [github.com/sqlalchemy/sqlalchemy](https://github.com/sqlalchemy/sqlalchemy) | SQL toolkit and Object Relational Mapper for persistent job and user metadata |
| **Alembic / SQLite3** | Standard | MIT / Public Domain | [sqlite.org](https://www.sqlite.org/) | Embedded relational database engine with zero external setup requirements |
| **Boto3** | 1.35.0+ | Apache-2.0 | [github.com/boto/boto3](https://github.com/boto/boto3) | AWS SDK for Python, providing S3-compatible integration with MinIO object storage |
| **PyYAML** | 6.0.2+ | MIT | [github.com/yaml/pyyaml](https://github.com/yaml/pyyaml) | Serialization and emission of OpenAPI 3.1.0 specifications |
| **Passlib[bcrypt]** | 1.7.4+ | BSD / Apache-2.0 | [foss.heptapod.net](https://foss.heptapod.net/python-libs/passlib) | Secure salted password hashing and validation using bcrypt |
| **PyJWT** | 2.9.0+ | MIT | [github.com/jpadilla/pyjwt](https://github.com/jpadilla/pyjwt) | RFC 7519 compliant JSON Web Token authentication and session claims |
| **Cryptography** | 43.0.0+ | Apache-2.0 / BSD | [github.com/pyca/cryptography](https://github.com/pyca/cryptography) | Cryptographic primitives, SHA-256 media hashing, and HMAC-SHA256 signature verification |
| **HTTPX** | 0.27.0+ | BSD-3-Clause | [github.com/encode/httpx](https://github.com/encode/httpx) | Asynchronous and synchronous HTTP client for URL media ingestion and callback webhooks |
| **Pytest** | 8.0.0+ / 9.0.2 | MIT | [github.com/pytest-dev/pytest](https://github.com/pytest-dev/pytest) | Automated testing framework for unit, integration, and E2E verification suites |

---

## 2. Media Processing & Transcoding Engine

| Technology | Recommended Version | License | Source / Repository | Purpose & Role |
|---|---|---|---|---|
| **FFmpeg** | 6.0+ / 9.0+ Essentials | LGPL-2.1+ / GPL-2.0+ | [ffmpeg.org](https://ffmpeg.org/) | Primary multimedia processing engine for video trimming, aspect ratio conversion, volume adjustments, subtitle burning, and stream manipulation |
| **FFprobe** | 6.0+ / 9.0+ | LGPL-2.1+ / GPL-2.0+ | [ffmpeg.org](https://ffmpeg.org/) | Multimedia stream analyzer for duration extraction, codec validation, resolution detection, and A/V sync drift verification |

*Note: All FFmpeg and FFprobe calls execute via explicit argument arrays in subprocesses without shell interpolation (`shell=False`), ensuring complete immunity against shell command injection.*

---

## 3. Frontend Architecture & User Interface (React Ecosystem)

| Library / Tool | Version | License | Source / Repository | Purpose & Role |
|---|---|---|---|---|
| **Node.js** | 20.0+ / 22.0+ | MIT | [nodejs.org](https://nodejs.org/) | JavaScript runtime environment for building frontend bundles |
| **React** | 18.3.1 | MIT | [github.com/facebook/react](https://github.com/facebook/react) | Core component-based declarative UI library |
| **React-DOM** | 18.3.1 | MIT | [github.com/facebook/react](https://github.com/facebook/react) | DOM rendering engine for React |
| **TypeScript** | 5.6.3 | Apache-2.0 | [github.com/microsoft/TypeScript](https://github.com/microsoft/TypeScript) | Static type checker providing robust compile-time safety |
| **Vite** | 5.4.11 | MIT | [github.com/vitejs/vite](https://github.com/vitejs/vite) | Next-generation frontend build tool, dev server, and asset bundler |
| **TailwindCSS** | 3.4.19 | MIT | [github.com/tailwindlabs/tailwindcss](https://github.com/tailwindlabs/tailwindcss) | Utility-first CSS framework for layout, design tokens, and responsive aesthetics |
| **PostCSS & Autoprefixer** | 8.4+ / 10.4+ | MIT | [github.com/postcss/postcss](https://github.com/postcss/postcss) | CSS preprocessing, vendor prefixing, and AST compilation |
| **Lucide React** | 0.475.0 | ISC | [lucide.dev](https://lucide.dev/) | Clean, accessible icon library for media controls and diagnostics |

---

## 4. Containerization & Storage Infrastructure

| Technology | Image / Version | License | Source / Repository | Purpose & Role |
|---|---|---|---|---|
| **Docker** | 20.10+ / 24.0+ | Apache-2.0 | [docker.com](https://www.docker.com/) | Container platform enabling reproducible container-based deployment |
| **Docker Compose** | 2.0+ | Apache-2.0 | [github.com/docker/compose](https://github.com/docker/compose) | Multi-container orchestration for backend, frontend, and storage services |
| **MinIO** | `minio/minio:latest` | AGPL-3.0 (Server) / Apache-2.0 (Client) | [min.io](https://min.io/) | High-performance, S3-compatible local object storage server |
| **Debian / Alpine** | 12 (Bookworm-slim) / 3.19 | GPL / BSD / MIT | [debian.org](https://www.debian.org/) | Lightweight container base images |

---

## 5. Typography, Design Tokens & Static Assets

| Asset / Font | Provider | License | Source | Purpose |
|---|---|---|---|---|
| **Plus Jakarta Sans** | Google Fonts (Tokotype) | SIL Open Font License 1.1 | [fonts.google.com](https://fonts.google.com/specimen/Plus+Jakarta+Sans) | Primary clean, modern UI typeface |
| **JetBrains Mono** | Google Fonts (JetBrains) | SIL Open Font License 1.1 | [fonts.google.com](https://fonts.google.com/specimen/JetBrains+Mono) | Monospace typeface for edit plans, hashes, and timing coordinates |
| **Synthetic Video Asset** | ClipPilot Project Generator | MIT / Public Domain | Bundled in `backend/tests/test_media` | Bundled synthetic test media generated in-memory via FFmpeg for zero-dependency testing |

---

## 6. Open Source License Compliance

All dependencies and software components integrated into ClipPilot AI use permissive, industry-standard open-source licenses (MIT, Apache 2.0, BSD-3-Clause, ISC, OFL 1.1, and LGPL 2.1). None of the dependencies impose viral copyleft restrictions on proprietary deployment when distributed in containerized microservices.
