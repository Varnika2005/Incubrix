import hashlib
import json
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from app.core.errors import format_error_payload
from app.database.session import SessionLocal
from app.database.models import IdempotencyRecord

class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only apply to mutating POST requests with Idempotency-Key header
        idempotency_key = request.headers.get("Idempotency-Key") or request.headers.get("idempotency-key")
        if request.method.upper() != "POST" or not idempotency_key:
            return await call_next(request)

        idempotency_key = idempotency_key.strip()
        if not idempotency_key:
            return await call_next(request)

        # Read request body
        body_bytes = await request.body()
        # Compute SHA256 of path + body
        path = request.url.path.rstrip("/")
        hasher = hashlib.sha256()
        hasher.update(f"{request.method.upper()}:{path}:".encode("utf-8"))
        hasher.update(body_bytes)
        current_hash = hasher.hexdigest()

        db = SessionLocal()
        try:
            record = db.query(IdempotencyRecord).filter(IdempotencyRecord.key == idempotency_key).first()
            if record:
                if record.request_hash == current_hash:
                    # Return exact cached response
                    headers = {"X-Idempotent-Replay": "true", "Content-Type": "application/json"}
                    return Response(
                        content=record.response_body,
                        status_code=record.response_status,
                        headers=headers,
                        media_type="application/json"
                    )
                else:
                    # Same key, differing payload -> Reject with HTTP 409 Conflict
                    return JSONResponse(
                        status_code=409,
                        content=format_error_payload(
                            code="IDEMPOTENCY_CONFLICT",
                            message="Idempotency key has already been used with a different request payload.",
                            retryable=False,
                            details={"idempotency_key": idempotency_key}
                        )
                    )
        finally:
            db.close()

        # Execute downstream route
        response = await call_next(request)

        # Cache successful or accepted responses (200, 201, 202)
        if 200 <= response.status_code < 300:
            # Consume response body to save it
            response_body = [section async for section in response.body_iterator]
            full_body_bytes = b"".join(response_body)
            full_body_str = full_body_bytes.decode("utf-8", errors="replace")

            # Try to extract job_id if present in JSON
            job_id = None
            try:
                data = json.loads(full_body_str)
                if isinstance(data, dict):
                    job_id = data.get("id") or data.get("job_id")
            except Exception:
                pass

            # Save in DB
            db = SessionLocal()
            try:
                new_record = IdempotencyRecord(
                    key=idempotency_key,
                    request_hash=current_hash,
                    response_status=response.status_code,
                    response_headers=json.dumps(dict(response.headers)),
                    response_body=full_body_str,
                    job_id=job_id
                )
                db.merge(new_record)
                db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()

            return Response(
                content=full_body_bytes,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type
            )

        return response
