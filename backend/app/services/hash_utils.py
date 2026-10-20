import hashlib
import os
from pathlib import Path
from typing import Tuple

class SourceIntegrityError(Exception):
    """Raised when an immutable source media file has been tampered with or modified."""
    pass

def calculate_file_sha256(file_path: str, chunk_size: int = 65536) -> str:
    """
    Computes a cryptographic SHA-256 digest of a media file.
    Reads in 64KB chunks for optimal memory usage on large video files.
    """
    p = Path(file_path)
    if not p.is_file():
        raise FileNotFoundError(f"Media file not found for hash calculation: {file_path}")
    
    sha = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(chunk_size):
            sha.update(chunk)
    return sha.hexdigest()

def verify_file_integrity(file_path: str, expected_hash: str) -> Tuple[bool, str]:
    """
    Verifies that the current SHA-256 hash of file_path matches expected_hash.
    Returns: (is_valid, current_hash)
    """
    current_hash = calculate_file_sha256(file_path)
    is_valid = (current_hash.lower() == expected_hash.lower())
    return is_valid, current_hash
