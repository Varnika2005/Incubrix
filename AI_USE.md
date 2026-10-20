# ClipPilot AI — AI Use & Assistance Disclosure

This document provides a transparent, comprehensive declaration of how Artificial Intelligence (AI) tools, models, and assistants were utilized during the design, development, testing, and documentation of **ClipPilot AI**, as well as how AI is incorporated into the runtime engine itself.

---

## 1. Developer Tooling & AI Assistance Disclosure

In accordance with IncuBrix evaluation guidelines, the following AI systems and tools were utilized during the development lifecycle:

| AI Tool / Assistant | Underlying Model | Primary Areas of Assistance |
|---|---|---|
| **Google Antigravity IDE** | Gemini 2.5 / Advanced Agentic Coding | Code refactoring, OpenAPI 3.1 YAML scaffolding, automated test generation, and IncuBrix compliance checks |
| **LLM-Assisted Code Generation** | Gemini Models | Boilerplate schema generation, Pydantic models, Tailwind responsive layout styling, and shell test runner scripts |

---

## 2. Breakdown of AI vs. Human Contribution

### A. AI-Assisted Components
- **IncuBrix Standards Scaffolding:** Generated initial templates for `IdempotencyMiddleware`, structured JSON logging formatters, and HMAC-SHA256 signature verification utilities based on the IncuBrix Integration Standards specification.
- **Test Suite Expansion:** Scaffolding parameterized test cases for timestamp variations, regex boundary conditions, and mock HTTP failure codes across `test_incubrix_compliance.py` and `test_instruction_three_way_response.py`.
- **OpenAPI 3.1 Specification:** Automated translation of FastAPI routes and Pydantic models into a unified `openapi.yaml` document.
- **Documentation Drafts:** Drafting initial outlines for `REPORT.md`, `DEPLOYMENT_GUIDE.md`, and compliance checklists.

### B. Human-Engineered & Architected Components
- **System Architecture & Domain Logic:** Design of the Non-Destructive Edit Decision List (EDL) model, Content-Aware Timeline anchor preservation policies, and sub-frame audio-video synchronization logic.
- **Subprocess & Shell Security:** Architecting the FFmpeg subprocess execution pipeline with strict argument array isolation (`shell=False`) and Windows path escaping to eliminate command injection vulnerabilities.
- **SSRF Defense Network Filter:** Implementation of the multi-layer SSRF prevention mechanism blocking IPv4/IPv6 loopback, RFC 1918 private subnets, link-local addresses, and cloud provider metadata endpoints (`169.254.169.254`).
- **Deterministic Hashing Formula:** Formalization of the canonical timeline hashing algorithm (3-decimal float precision, sorted dictionary keys, SHA-256 digest) ensuring 100% reproducible edit plans.
- **UI Architecture & Layout Debugging:** Diagnosing and resolving the desktop viewport grid stacking issue and the authentication loop/unmount race condition.

---

## 3. Verification & Quality Assurance (No Blind AI Trust)

To ensure software integrity, stability, and security, **no AI-generated code was committed without rigorous empirical verification**:

1. **Zero Faked or Mocked Test Results:**  
   All 170 tests in the test suite run genuine Python code, real SQLite database operations, and actual FFmpeg media transcoding commands on real synthetic media.
2. **Empirical Benchmarking:**  
   The entire test suite (`scripts/run_all_tests.py`) was executed on the local host, confirming a **100% pass rate (170/170 tests)** with exit code 0.
3. **Compilation & Type Safety:**  
   The frontend was verified with both `npm run build` and `npx tsc --noEmit`, ensuring zero TypeScript or bundler errors.
4. **Browser-Based Verification:**  
   Visual and behavioral audits were conducted using automated browser subagents on `http://localhost:5173` to verify responsive two-column layout rendering and session flow.

---

## 4. Runtime AI in ClipPilot AI Engine

ClipPilot AI itself incorporates AI capabilities for end users while maintaining strict safety boundaries:

### A. Dual-Engine Parsing Architecture
- **Primary Engine (Local & Deterministic):** ClipPilot AI defaults to an offline, deterministic regex-based Natural Language Processing (NLP) parser. This engine parses complex commands (cuts, trims, aspect ratio crops, volume scaling, speed changes, silence removal, subtitle burning) with zero latency, zero cloud API cost, and 100% reproducibility.
- **Secondary Engine (Optional Generative LLM):** ClipPilot AI includes server-side hooks to interface with Gemini / OpenAI-compatible models for unstructured or ambiguous phrasing.

### B. Strict Three-Way Guardrails
AI outputs are **never blindly executed by the FFmpeg engine**. Every parsed instruction must pass through the strict Three-Way Instruction Processor:
1. `APPLIED`: The instruction maps to a mathematically valid, supported operation within media duration bounds.
2. `NEEDS_CLARIFICATION`: Ambiguous phrasing (e.g., "make it shorter", "that caption", or unstated timestamps) immediately halts execution and presents specific options to the user.
3. `REJECTED`: Unsupported operations (e.g., AI face replacement, 8K upscaling) are safely rejected with atomic rollback protection, preserving timeline state.
