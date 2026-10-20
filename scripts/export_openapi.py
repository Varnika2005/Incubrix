import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import yaml
from fastapi.openapi.utils import get_openapi
from app.main import app

def export_openapi():
    schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version="3.1.0",
        description=app.description,
        routes=app.routes,
    )
    
    out_file = Path(__file__).resolve().parent.parent / "openapi.yaml"
    with open(out_file, "w", encoding="utf-8") as f:
        yaml.dump(schema, f, sort_keys=False, allow_unicode=True)
    print(f"Exported valid OpenAPI 3.1 YAML to {out_file}")

if __name__ == "__main__":
    export_openapi()
