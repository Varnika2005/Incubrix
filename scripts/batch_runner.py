#!/usr/bin/env python3
"""
ClipPilot AI — IncuBrix Batch Runner CLI
Automated batch processing test harness.
Submits media to ClipPilot AI HTTP API, monitors background job execution,
and saves outputs, manifests, receipts, and status receipts.

Usage:
  python scripts/batch_runner.py --input sample_assets/sample_talking_head.mp4 --output-dir batch_results
  python scripts/batch_runner.py --input sample_assets/ --output-dir batch_results --api-url http://127.0.0.1:8000
"""

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}

def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def run_batch(
    input_path: Path,
    output_dir: Path,
    api_url: str = "http://127.0.0.1:8000",
    timeout_seconds: float = 180.0,
    poll_interval: float = 1.0,
    prompt: str = "Cut the first 2 seconds, convert to 9:16 vertical, and boost volume",
    auth_token: Optional[str] = None,
    client: Optional[Any] = None
) -> int:
    api_url = api_url.rstrip("/")
    api_v1 = f"{api_url}/api/v1"

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Discover target media inputs
    media_files: List[Path] = []
    if input_path.is_file():
        if input_path.suffix.lower() in ALLOWED_EXTENSIONS:
            media_files.append(input_path)
        else:
            log(f"ERROR: Input file '{input_path}' has unsupported extension. Allowed: {ALLOWED_EXTENSIONS}")
            return 1
    elif input_path.is_dir():
        for p in input_path.iterdir():
            if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS:
                media_files.append(p)
        if not media_files:
            log(f"WARNING: No supported media files found in directory '{input_path}'.")
            return 1
    else:
        log(f"ERROR: Input path '{input_path}' does not exist.")
        return 1

    log(f"Starting ClipPilot Batch Runner: {len(media_files)} item(s) to process.")
    log(f"API Target: {api_url}")
    log(f"Output Directory: {output_dir.resolve()}")

    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    overall_results: List[Dict[str, Any]] = []
    failed_count = 0

    http_client = client or httpx.Client(timeout=30.0)
    try:
        # Pre-flight: verify liveness and readiness
        try:
            r_health = http_client.get(f"{api_url}/health")
            if r_health.status_code != 200:
                log(f"ERROR: Health check failed: {r_health.text}")
                return 1
            r_ready = http_client.get(f"{api_url}/ready")
            if r_ready.status_code != 200:
                log(f"WARNING: Readiness check returned HTTP {r_ready.status_code}: {r_ready.text}")
            log(f"Connected to ClipPilot service (v{r_health.json().get('version', 'unknown')}). Ready.")
        except Exception as e:
            log(f"ERROR: Could not connect to ClipPilot API at {api_url}: {e}")
            return 1

        for idx, media_file in enumerate(media_files, start=1):
            log(f"\n--- [{idx}/{len(media_files)}] Processing: {media_file.name} ---")
            item_summary: Dict[str, Any] = {
                "input_file": str(media_file.resolve()),
                "filename": media_file.name,
                "status": "pending",
                "start_time": time.time(),
            }

            try:
                # 1. Upload or create job
                upload_start = time.time()
                with open(media_file, "rb") as f:
                    files = {"file": (media_file.name, f, "video/mp4")}
                    # If auth_token not provided, allow demo job creation or authenticated upload
                    r_upload = http_client.post(
                        f"{api_v1}/jobs/upload",
                        files=files,
                        headers=headers,
                        timeout=60.0
                    )

                # Fallback to demo endpoint if unauthenticated upload is rejected
                if r_upload.status_code in (401, 403) and not auth_token:
                    log("   Unauthenticated upload restricted; initializing via standard demo job...")
                    r_upload = http_client.post(f"{api_v1}/jobs/demo", headers=headers)

                if r_upload.status_code not in (200, 201):
                    raise RuntimeError(f"Upload failed (HTTP {r_upload.status_code}): {r_upload.text}")

                job_data = r_upload.json()
                job_id = job_data.get("job_id") or job_data.get("id")
                item_summary["job_id"] = job_id
                log(f"   [OK] Job Created: ID={job_id}")

                # 2. Analyze prompt (if edit plan not already generated)
                edit_plan = job_data.get("edit_plan")
                if not edit_plan:
                    log(f"   Analyzing prompt: '{prompt}'...")
                    r_analyze = http_client.post(
                        f"{api_v1}/jobs/{job_id}/analyze",
                        headers=headers,
                        json={"prompt": prompt}
                    )
                    if r_analyze.status_code != 200:
                        raise RuntimeError(f"Prompt analysis failed: {r_analyze.text}")
                    edit_plan = r_analyze.json().get("edit_plan")

                # 3. Submit background job with Idempotency-Key
                idempotency_key = f"clippilot-batch-{job_id}-{uuid.uuid4().hex[:8]}"
                proc_headers = {**headers, "Idempotency-Key": idempotency_key}
                log(f"   Submitting background processing (Idempotency-Key={idempotency_key[:24]}...)...")

                r_proc = http_client.post(
                    f"{api_v1}/jobs/{job_id}/process",
                    headers=proc_headers,
                    json={"approved_plan": edit_plan}
                )
                if r_proc.status_code not in (200, 202):
                    raise RuntimeError(f"Processing submission failed (HTTP {r_proc.status_code}): {r_proc.text}")

                log(f"   [OK] Job Accepted (HTTP {r_proc.status_code})")

                # 4. Poll GET /api/v1/jobs/{job_id} until succeeded or failed
                poll_start = time.time()
                completed = False
                job_state = None

                while time.time() - poll_start < timeout_seconds:
                    r_poll = http_client.get(f"{api_v1}/jobs/{job_id}", headers=headers)
                    if r_poll.status_code != 200:
                        raise RuntimeError(f"Polling failed (HTTP {r_poll.status_code}): {r_poll.text}")

                    job_state = r_poll.json()
                    st = job_state.get("status")
                    std_st = job_state.get("standard_status", st)
                    prog = job_state.get("progress", 0)

                    log(f"   ... Status: {st} ({std_st}) | Progress: {prog}%")

                    if st in ("succeeded", "completed") or std_st == "succeeded":
                        completed = True
                        break
                    elif st == "failed" or std_st == "failed":
                        err = job_state.get("error_message") or job_state.get("error")
                        raise RuntimeError(f"Job marked failed by worker: {err}")

                    time.sleep(poll_interval)

                if not completed:
                    raise TimeoutError(f"Job timed out after {timeout_seconds} seconds")

                item_summary["status"] = "succeeded"
                item_summary["duration_seconds"] = round(time.time() - item_summary["start_time"], 2)
                log(f"   [PASS] Job Completed in {item_summary['duration_seconds']}s")

                # 5. Download results: MP4, Manifest, and Receipt
                # Download Output Video
                dl_url = f"{api_v1}/jobs/{job_id}/download"
                r_dl = http_client.get(dl_url, headers=headers)
                if r_dl.status_code == 200:
                    out_video_path = output_dir / f"{job_id}_{media_file.stem}_edited.mp4"
                    out_video_path.write_bytes(r_dl.content)
                    item_summary["output_video"] = str(out_video_path.name)
                    log(f"   Saved output video ({len(r_dl.content):,} bytes) -> {out_video_path.name}")

                # Download Output Manifest
                manifest_url = f"{api_v1}/jobs/{job_id}/manifest"
                r_man = http_client.get(manifest_url, headers=headers)
                if r_man.status_code == 200:
                    out_man_path = output_dir / f"{job_id}_manifest.json"
                    out_man_path.write_text(json.dumps(r_man.json(), indent=2), encoding="utf-8")
                    item_summary["manifest"] = str(out_man_path.name)
                    log(f"   Saved output manifest -> {out_man_path.name}")

                # Download Receipt
                rcpt_url = f"{api_v1}/jobs/{job_id}/receipt"
                r_rcpt = http_client.get(rcpt_url, headers=headers)
                if r_rcpt.status_code == 200:
                    out_rcpt_path = output_dir / f"{job_id}_receipt.json"
                    out_rcpt_path.write_text(json.dumps(r_rcpt.json(), indent=2), encoding="utf-8")
                    item_summary["receipt"] = str(out_rcpt_path.name)
                    log(f"   Saved edit receipt -> {out_rcpt_path.name}")

            except Exception as e:
                item_summary["status"] = "failed"
                item_summary["error"] = str(e)
                item_summary["duration_seconds"] = round(time.time() - item_summary["start_time"], 2)
                failed_count += 1
                log(f"   [FAIL] Error processing {media_file.name}: {e}")

            # Save individual item status
            status_file = output_dir / f"{item_summary.get('job_id', media_file.stem)}_status.json"
            status_file.write_text(json.dumps(item_summary, indent=2), encoding="utf-8")
            overall_results.append(item_summary)
    finally:
        if client is None and hasattr(http_client, "close"):
            http_client.close()
    summary_path = output_dir / "batch_summary.json"
    batch_summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_items": len(media_files),
        "succeeded": len(media_files) - failed_count,
        "failed": failed_count,
        "results": overall_results
    }
    summary_path.write_text(json.dumps(batch_summary, indent=2), encoding="utf-8")

    log("\n=================== BATCH SUMMARY ===================")
    log(f"Total: {len(media_files)} | Succeeded: {len(media_files) - failed_count} | Failed: {failed_count}")
    log(f"Full batch report saved to: {summary_path.resolve()}")
    log("=====================================================")

    return 0 if failed_count == 0 else 1

def main():
    parser = argparse.ArgumentParser(
        description="ClipPilot AI IncuBrix Batch Runner — Process media files via HTTP API"
    )
    parser.add_argument("--input", "-i", type=Path, default=Path("sample_assets/sample_1_talking_head.mp4"),
                        help="Path to media file or folder of media files to process")
    parser.add_argument("--output-dir", "-o", type=Path, default=Path("batch_results"),
                        help="Directory where output videos, manifests, receipts and logs will be saved")
    parser.add_argument("--api-url", "-u", type=str, default="http://127.0.0.1:8000",
                        help="Base API URL for the running ClipPilot instance")
    parser.add_argument("--timeout", "-t", type=float, default=180.0,
                        help="Maximum processing timeout per item in seconds")
    parser.add_argument("--poll-interval", "-p", type=float, default=1.0,
                        help="Interval in seconds between job polling requests")
    parser.add_argument("--prompt", type=str, default="Cut the first 2 seconds, convert to 9:16 vertical, and boost volume",
                        help="Natural language editing instruction to apply to the videos")
    parser.add_argument("--auth-token", type=str, default=None,
                        help="Optional Bearer token for authenticated project access")

    args = parser.parse_args()
    exit_code = run_batch(
        input_path=args.input,
        output_dir=args.output_dir,
        api_url=args.api_url,
        timeout_seconds=args.timeout,
        poll_interval=args.poll_interval,
        prompt=args.prompt,
        auth_token=args.auth_token
    )
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
