import hashlib
import hmac
import json
import logging
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

async def dispatch_job_callback(
    callback_url: str,
    payload: Dict[str, Any],
    secret: Optional[str] = None
) -> bool:
    """
    Send an HTTP POST callback to callback_url with payload signed via HMAC-SHA256
    in the X-IncuBrix-Signature header.
    """
    if not callback_url:
        return False

    signing_secret = (secret or settings.CALLBACK_SECRET or settings.SECRET_KEY).encode("utf-8")
    payload_bytes = json.dumps(payload, separators=(',', ':'), default=str).encode("utf-8")
    
    # Compute HMAC-SHA256 hex digest
    signature = hmac.new(signing_secret, payload_bytes, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-IncuBrix-Signature": f"sha256={signature}",
        "X-Signature-Algorithm": "HMAC-SHA256"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.post(callback_url, content=payload_bytes, headers=headers)
            if resp.status_code < 300:
                logger.info(f"Successfully dispatched signed IncuBrix callback to {callback_url} (HTTP {resp.status_code})")
                return True
            else:
                logger.warning(f"IncuBrix callback to {callback_url} returned HTTP {resp.status_code}: {resp.text[:200]}")
                return False
    except Exception as e:
        logger.error(f"Failed to dispatch IncuBrix callback to {callback_url}: {e}")
        return False
