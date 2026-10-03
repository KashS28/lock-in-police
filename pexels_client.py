from __future__ import annotations

import os
import random
import tempfile

import requests
from dotenv import load_dotenv

load_dotenv()

SEARCH_QUERIES = [
    "angry baby",
    "grumpy baby",
    "pouting toddler",
    "disappointed baby",
    "frustrated baby face",
    "grumpy cat face",
    "angry puppy",
    "disapproving dog",
    "judging cat",
    "grumpy bulldog",
    "annoyed hamster",
]

def fetch_image(timeout: int = 4) -> str | None:
    """Download a random Pexels image and return the local temp file path, or None."""
    api_key = os.getenv("PEXELS_API_KEY", "")
    if not api_key or api_key == "your_pexels_api_key_here":
        return None

    query = random.choice(SEARCH_QUERIES)

    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": 15, "orientation": "landscape"},
            timeout=timeout,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if not photos:
            return None
        photo = random.choice(photos)
        img_url = photo["src"]["large"]
        max_bytes = 5 * 1024 * 1024  # 5 MB cap
        with requests.get(img_url, timeout=timeout, stream=True) as r:
            r.raise_for_status()
            chunks, size = [], 0
            for chunk in r.iter_content(8192):
                size += len(chunk)
                if size > max_bytes:
                    return None
                chunks.append(chunk)
            img_data = b"".join(chunks)
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False, prefix="lockInImg_")
        tmp.write(img_data)
        tmp.close()
        return tmp.name
    except Exception:
        return None
