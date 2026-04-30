import base64
import io
from datetime import datetime, timezone

import streamlit as st
from groq import Groq
from PIL import Image

VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
VISION_MODEL_FALLBACK = "llama-3.2-11b-vision-preview"


class OCRError(Exception):
    pass


def _to_jpeg_base64(image_bytes: bytes) -> str:
    pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    buf = io.BytesIO()
    pil.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def run_enhanced_ocr(image_bytes: bytes, image_name: str = "image") -> dict:
    try:
        pil = Image.open(io.BytesIO(image_bytes))
        width, height = pil.size
    except Exception as e:
        raise OCRError(f"Cannot open image: {e}")

    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except KeyError:
        raise OCRError("GROQ_API_KEY not found in Streamlit secrets.")

    client = Groq(api_key=api_key)
    b64 = _to_jpeg_base64(image_bytes)

    prompt = (
        "Extract ALL text from this image exactly as it appears. "
        "Preserve the original line breaks and paragraph structure. "
        "Return only the extracted text — no commentary, no labels, no markdown."
    )

    raw_text = ""
    model_used = VISION_MODEL

    for model in [VISION_MODEL, VISION_MODEL_FALLBACK]:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                max_tokens=2048,
                temperature=0.0,
            )
            raw_text = (response.choices[0].message.content or "").strip()
            model_used = model
            break
        except Exception as e:
            if model == VISION_MODEL_FALLBACK:
                raise OCRError(f"Vision OCR failed on all models: {e}")
            continue

    words = [w for w in raw_text.split() if w.strip()]
    lines = [l for l in raw_text.splitlines() if l.strip()]

    return {
        "raw_text": raw_text,
        "confidence": 95.0 if words else 0.0,
        "word_count": len(words),
        "line_count": len(lines),
        "layout_hints": {"avg_line_gap": 0, "indent_levels": [], "height_variance": 0.0,
                         "dominant_height": 12, "line_count": len(lines)},
        "preprocessing_applied": f"vision:{model_used}",
        "ocr_engine": "vision",
        "image_dimensions": (width, height),
        "image_name": image_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
