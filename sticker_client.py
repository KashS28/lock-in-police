#!/usr/bin/env python3
"""Fetch a random cute-angry GIF sticker and cache it locally."""
import hashlib
import os
import random

import requests

_APP_DIR   = os.path.dirname(os.path.abspath(__file__))
_CACHE_DIR = os.path.join(_APP_DIR, "assets", "stickers")

# Cute angry/pouty stickers — direct Giphy CDN (no API key needed)
_STICKER_IDS = [
    "lD2qFeJzjtG52UDtCm",   # angry cat
    "3o6nUWtsrEqktR2fcY",   # anime pout
    "Io6mCqHwz1nXvaz5tg",   # pikachu mad
    "9HXmQYoNSOE946ncsm",   # molang upset
    "RKNYxAq5w5O8ASk9F8",   # pusheen angry
    "aFeDUVD2St7IKbaYWf",   # hamster pout
    "4rEN32LaD7O8foQyXD",   # bunny grumpy
    "xT1R9PEZI7wGURas0g",   # chibi maruko
]


def fetch_sticker():
    """Return a local path to a cached cute-angry GIF, or None on failure."""
    os.makedirs(_CACHE_DIR, exist_ok=True)
    gid = random.choice(_STICKER_IDS)
    url = f"https://media.giphy.com/media/{gid}/giphy.gif"
    try:
        fname = gid + ".gif"
        path  = os.path.join(_CACHE_DIR, fname)
        if not os.path.exists(path):
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            with open(path, "wb") as f:
                f.write(resp.content)
        return path
    except Exception:
        return None
