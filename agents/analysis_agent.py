import json
import time

import streamlit as st
from groq import Groq

MODEL_PRIMARY = "qwen/qwen3-32b"
MODEL_FALLBACK = "llama-3.3-70b-versatile"

BLOCK_TYPES = ["heading", "paragraph", "bullet_list", "numbered_list", "table", "table_cell", "caption", "footer", "unknown"]
ALIGNMENTS = ["left", "center", "right", "justified"]
FONT_SIZES = ["large", "medium", "small"]


class GroqUnavailableError(Exception):
    pass


def _get_client() -> Groq:
    try:
        api_key = st.secrets["GROQ_API_KEY"]
        return Groq(api_key=api_key)
    except KeyError:
        raise GroqUnavailableError("GROQ_API_KEY not found in Streamlit secrets.")
    except Exception as e:
        raise GroqUnavailableError(f"Cannot initialize Groq client: {e}")


def _select_model(ocr_confidence: float, text_length: int) -> str:
    return MODEL_PRIMARY


def _format_patterns(patterns: list) -> str:
    if not patterns:
        return "None yet."
    lines = []
    for p in patterns[:10]:
        lines.append(
            f"- When OCR type is '{p['original_type']}' and text matches '{p['trigger']}', "
            f"prefer '{p['inferred_type']}' (confidence: {p['confidence']:.0%}, seen {p['observed_count']}x)"
        )
    return "\n".join(lines)


def _format_corrections(corrections: list) -> str:
    if not corrections:
        return "None this session."
    recent = corrections[-5:]
    lines = []
    for c in recent:
        lines.append(
            f"- Block '{c['block_id']}': '{c['original_type']}' → '{c['corrected_type']}' "
            f"(text: \"{c['text_snippet'][:40]}\")"
        )
    return "\n".join(lines)


def _build_prompt(ocr_result: dict, user_preferences: dict, session_corrections: list) -> tuple[str, str]:
    system_prompt = """You are a Document Formatting Agent embedded in an intelligent OCR system.

Your task: analyze raw OCR text extracted from a scanned document image and classify every block of text with its correct formatting.

OUTPUT RULES:
- Return ONLY valid JSON. No prose, no markdown fences, no explanations outside the JSON.
- The JSON must have exactly these top-level keys: document_type, confidence_score, reasoning, blocks, warnings
- Every item in "blocks" must have: id, text, block_type, level, alignment, bold, italic, font_size_hint, confidence, reasoning

BLOCK TYPES (use exactly these strings):
- heading (use "level": 1, 2, or 3)
- paragraph
- bullet_list
- numbered_list
- table (use for rows of tabular/columnar data)
- table_cell
- caption
- footer
- unknown

ALIGNMENT: left | center | right | justified
FONT SIZE HINT: large | medium | small

CONFIDENCE RULES:
- Set block confidence < 0.70 when you are uncertain — add the block's id to warnings
- Set document-level confidence_score as the mean of block confidences
- Always provide a "reasoning" field per block explaining your decision in one sentence

EVIDENCE TO USE:
1. Text content (capitalization, length, punctuation)
2. Layout hints (line gaps, indentation, word height variance)
3. User's learned preferences from past sessions
4. User's corrections made in the current session (highest priority)"""

    hints = ocr_result.get("layout_hints", {})
    user_message = f"""=== RAW OCR TEXT ===
{ocr_result.get('raw_text', '').strip()}

=== OCR METRICS ===
- Mean word confidence: {ocr_result.get('confidence', 0)}%
- Word count: {ocr_result.get('word_count', 0)}
- Line count: {ocr_result.get('line_count', 0)}

=== LAYOUT HINTS (from word-level OCR analysis) ===
- Average line gap (pixels): {hints.get('avg_line_gap', 'N/A')}
- Indentation levels detected (pixels from left): {hints.get('indent_levels', [])}
- Word height variance: {hints.get('height_variance', 'N/A')} (higher = more font size diversity = likely has headings)
- Dominant word height: {hints.get('dominant_height', 'N/A')}px
- Detected line count: {hints.get('line_count', 'N/A')}

=== LEARNED USER PREFERENCES (from past sessions) ===
{_format_patterns(user_preferences.get('learned_patterns', []))}

=== USER CORRECTIONS THIS SESSION (highest priority signals) ===
{_format_corrections(session_corrections)}

Now analyze the document and return the JSON object."""

    return system_prompt, user_message


def _validate_response(data: dict) -> bool:
    required_top = {"document_type", "confidence_score", "reasoning", "blocks", "warnings"}
    if not required_top.issubset(data.keys()):
        return False
    if not isinstance(data["blocks"], list):
        return False
    required_block = {"id", "text", "block_type", "level", "alignment", "bold", "italic", "font_size_hint", "confidence", "reasoning"}
    for block in data["blocks"]:
        if not required_block.issubset(block.keys()):
            return False
    return True


def _parse_and_validate(content: str) -> dict | None:
    try:
        data = json.loads(content)
        if _validate_response(data):
            return data
        return None
    except (json.JSONDecodeError, ValueError):
        return None


def analyze_document(ocr_result: dict, user_preferences: dict, session_corrections: list) -> dict:
    try:
        client = _get_client()
    except GroqUnavailableError as e:
        return {"status": "error", "error_message": str(e), "blocks": [], "warnings": [str(e)]}

    system_prompt, user_message = _build_prompt(ocr_result, user_preferences, session_corrections)
    model = _select_model(ocr_result.get("confidence", 0), ocr_result.get("word_count", 0))

    for attempt, current_model in enumerate([MODEL_PRIMARY, MODEL_FALLBACK]):
        try:
            t_start = time.monotonic()
            response = client.chat.completions.create(
                model=current_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=4096,
            )
            elapsed_ms = int((time.monotonic() - t_start) * 1000)
            content = response.choices[0].message.content
            data = _parse_and_validate(content)

            if data is not None:
                data["status"] = "success"
                data["model_used"] = current_model
                data["tokens_used"] = response.usage.total_tokens if response.usage else 0
                data["processing_time_ms"] = elapsed_ms
                return data

        except Exception as e:
            if attempt == 1:
                return {
                    "status": "error",
                    "error_message": f"Groq API error: {e}",
                    "blocks": [],
                    "warnings": [f"API error: {e}"],
                    "model_used": current_model,
                    "tokens_used": 0,
                    "processing_time_ms": 0,
                }

    return {
        "status": "error",
        "error_message": "Failed to get valid JSON from Groq after 2 attempts.",
        "blocks": [],
        "warnings": ["JSON validation failed on both model attempts."],
        "model_used": model,
        "tokens_used": 0,
        "processing_time_ms": 0,
    }
