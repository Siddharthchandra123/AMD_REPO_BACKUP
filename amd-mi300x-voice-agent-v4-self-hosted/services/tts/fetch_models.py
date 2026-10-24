"""Ensure the Kokoro model files exist when building the TTS image.

Downloaded only when missing; from pinned upstream v1.0 release assets.
"""
import hashlib
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen

DEST = Path("/app/models")
DEST.mkdir(parents=True, exist_ok=True)
BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
MODELS = {"kokoro-v1.0.onnx": 50_000_000, "voices-v1.0.bin": 1_000_000}

for filename, minimum_size in MODELS.items():
    path = DEST / filename
    if path.exists() and path.stat().st_size >= minimum_size:
        print(f"Keeping existing {filename} ({path.stat().st_size:,} bytes)", flush=True)
        continue
    url = f"{BASE}/{filename}"
    partial = path.with_name(path.name + ".part")
    for attempt in range(1, 4):
        try:
            print(f"Fetching missing {filename} (attempt {attempt}/3)...", flush=True)
            request = Request(url, headers={"User-Agent": "AMD-Voice-Agent/1.0"})
            sha = hashlib.sha256()
            total = 0
            with urlopen(request, timeout=180) as source, partial.open("wb") as out:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    sha.update(chunk)
                    total += len(chunk)
            if total < minimum_size:
                raise RuntimeError(f"Download too small: {total} bytes")
            expected = os.getenv("KOKORO_" + filename.upper().replace('-', '_').replace('.', '_') + "_SHA256")
            if expected and sha.hexdigest().lower() != expected.lower():
                raise ValueError("SHA-256 did not match provided checksum")
            partial.replace(path)
            print(f"Downloaded {filename}: {total:,} bytes, sha256={sha.hexdigest()}", flush=True)
            break
        except Exception as exc:
            partial.unlink(missing_ok=True)
            if attempt == 3:
                raise RuntimeError(f"Could not fetch {filename} from pinned upstream release") from exc
            print(f"Download retry: {exc}", flush=True)
            time.sleep(3 * attempt)
