"""Crop-health image assessment (FR-09, PRD §5.8).

Deliberately has no mock fallback. A fabricated diagnosis would violate PRD §17
("never fabricate data", "never present preliminary analysis as confirmed"), so
when the model is unavailable this returns an explicit unavailable result.
"""
from __future__ import annotations

import io
import json
import logging
import re
from typing import Any

from ..config import CROP_HEALTH_DISCLAIMER, get_secret, llm_provider, vision_model

log = logging.getLogger(__name__)

MAX_BYTES = 5 * 1024 * 1024
MIN_DIMENSION = 64
MAX_DIMENSION = 8000
ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}

PROMPT = """You are a plant-health assistant looking at a photo of a crop or leaf \
from a farm in Pakistan.

Give a PRELIMINARY visual assessment only. You are not diagnosing. If the image is \
not a plant, or is too blurry or dark to assess, say so in "condition" and set \
confidence to 0.

Return ONLY valid JSON, no code fences, in exactly this shape:
{
  "condition": "short name of the most likely condition, or 'Unable to assess'",
  "confidence": 0.0,
  "severity": "none | mild | moderate | severe | unknown",
  "symptoms": ["visible symptom", "..."],
  "next_steps": ["practical action a farmer can take", "..."]
}"""


class ImageValidationError(ValueError):
    """Raised for images we refuse to send to the model."""


def validate_image(data: bytes, mime: str | None = None) -> tuple[str, tuple[int, int]]:
    """Check type, size and dimensions before any network call (PRD §9).

    Returns (detected_mime, (width, height)). Raises ImageValidationError.
    """
    if not data:
        raise ImageValidationError("The file is empty.")
    if len(data) > MAX_BYTES:
        raise ImageValidationError(
            f"Image is {len(data) / 1024 / 1024:.1f} MB. The limit is "
            f"{MAX_BYTES // 1024 // 1024} MB. Please upload a smaller photo."
        )
    if mime and mime.lower() not in ALLOWED_MIME:
        raise ImageValidationError(
            f"'{mime}' is not a supported image type. Please upload a JPG, PNG or WEBP file."
        )

    try:
        from PIL import Image
    except ImportError:
        raise ImageValidationError("Image support is not installed on the server.") from None

    try:
        # verify() checks the header, then the file must be reopened to read it.
        probe = Image.open(io.BytesIO(data))
        probe.verify()
        image = Image.open(io.BytesIO(data))
        detected_format = (image.format or "").upper()
        width, height = image.size
    except Exception:
        raise ImageValidationError(
            "That file could not be read as an image. Please upload a JPG, PNG or WEBP photo."
        ) from None

    if detected_format not in ALLOWED_FORMATS:
        raise ImageValidationError(
            f"The file is a {detected_format or 'unknown'} image. Please upload a JPG, PNG or WEBP photo."
        )
    if min(width, height) < MIN_DIMENSION:
        raise ImageValidationError(
            f"Image is only {width}x{height} pixels, too small to assess. "
            "Please upload a clearer, closer photo."
        )
    if max(width, height) > MAX_DIMENSION:
        raise ImageValidationError(f"Image is larger than {MAX_DIMENSION} pixels on one side.")

    return f"image/{detected_format.lower()}", (width, height)


def _parse_json(raw: str) -> dict | None:
    text = re.sub(r"^\s*```(?:json)?|```\s*$", "", (raw or "").strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return None


def _call_gemini_vision(data: bytes, mime: str) -> str | None:
    api_key = get_secret("LLM_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=vision_model(),
            contents=[
                types.Part.from_bytes(data=data, mime_type=mime),
                PROMPT,
            ],
            config=types.GenerateContentConfig(
                temperature=0.2, response_mime_type="application/json"
            ),
        )
        return response.text
    except ImportError:
        log.warning("google-genai is not installed; uncomment it in requirements.txt")
        return None
    except Exception as exc:
        log.warning("Vision call failed: %s: %s", type(exc).__name__, exc)
        return None


def unavailable_result(reason: str) -> dict[str, Any]:
    return {
        "available": False,
        "condition": "Assessment unavailable",
        "confidence": 0.0,
        "severity": "unknown",
        "symptoms": [],
        "next_steps": [
            "Photograph several affected leaves in daylight and show them to your local "
            "agriculture extension officer or a nearby input dealer.",
        ],
        "reason": reason,
        "disclaimer": CROP_HEALTH_DISCLAIMER,
    }


def assess_image(data: bytes, mime: str | None = None) -> dict[str, Any]:
    """Preliminary visual assessment. Validates first, never raises for callers."""
    detected_mime, size = validate_image(data, mime)   # may raise ImageValidationError

    if llm_provider() != "gemini":
        return unavailable_result(f"Vision is not wired up for provider '{llm_provider()}'.")

    raw = _call_gemini_vision(data, detected_mime)
    if raw is None:
        return unavailable_result(
            "The image assessment model is not configured or could not be reached."
        )

    parsed = _parse_json(raw)
    if not parsed or not parsed.get("condition"):
        return unavailable_result("The model returned a response that could not be read.")

    try:
        confidence = max(0.0, min(1.0, float(parsed.get("confidence", 0))))
    except (TypeError, ValueError):
        confidence = 0.0

    symptoms = parsed.get("symptoms") or []
    steps = parsed.get("next_steps") or []
    return {
        "available": True,
        "condition": str(parsed["condition"]),
        "confidence": confidence,
        "severity": str(parsed.get("severity", "unknown")).lower(),
        "symptoms": [str(s) for s in symptoms][:8],
        "next_steps": [str(s) for s in steps][:6],
        "image_size": size,
        # The disclaimer is appended here, never taken from the model.
        "disclaimer": CROP_HEALTH_DISCLAIMER,
    }
