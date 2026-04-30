import json
import os
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

PREFS_PATH = "data/preferences.json"
LOG_PATH = "logs/agent_log.json"
MAX_LOG_ENTRIES = 100
MAX_PATTERNS = 20

_DEFAULT_PREFS = {
    "version": "1.0",
    "created_at": None,
    "last_updated": None,
    "corrections_count": 0,
    "session_count": 0,
    "learned_patterns": [],
    "feedback_history": [],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_session_state() -> None:
    defaults = {
        "pipeline_stage": "idle",
        "ocr_result": None,
        "analysis_result": None,
        "current_overrides": {},
        "corrections": [],
        "bypass_ai": False,
        "feedback_submitted": False,
        "current_image_name": None,
        "image_bytes": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def load_preferences(path: str = PREFS_PATH) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            prefs = json.load(f)
        for key, value in _DEFAULT_PREFS.items():
            prefs.setdefault(key, value)
        return prefs
    except (FileNotFoundError, json.JSONDecodeError):
        prefs = _DEFAULT_PREFS.copy()
        prefs["created_at"] = _now()
        return prefs


def save_preferences(prefs: dict, path: str = PREFS_PATH) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    prefs["last_updated"] = _now()
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=2)
    os.replace(tmp_path, path)


def record_correction(block_id: str, original_block: dict, corrected_block: dict) -> None:
    correction = {
        "block_id": block_id,
        "original_type": original_block.get("block_type", "unknown"),
        "corrected_type": corrected_block.get("block_type", "unknown"),
        "original_alignment": original_block.get("alignment", "left"),
        "corrected_alignment": corrected_block.get("alignment", "left"),
        "original_bold": original_block.get("bold", False),
        "corrected_bold": corrected_block.get("bold", False),
        "text_snippet": original_block.get("text", "")[:60],
        "timestamp": _now(),
    }
    if "corrections" not in st.session_state:
        st.session_state["corrections"] = []
    existing_ids = [c["block_id"] for c in st.session_state["corrections"]]
    if block_id in existing_ids:
        st.session_state["corrections"] = [
            c if c["block_id"] != block_id else correction
            for c in st.session_state["corrections"]
        ]
    else:
        st.session_state["corrections"].append(correction)


def update_learned_patterns(prefs: dict, corrections: list) -> dict:
    if not corrections:
        return prefs

    prefs["corrections_count"] = prefs.get("corrections_count", 0) + len(corrections)
    patterns = prefs.get("learned_patterns", [])

    for correction in corrections:
        orig_type = correction["original_type"]
        corr_type = correction["corrected_type"]
        if orig_type == corr_type:
            continue

        text = correction.get("text_snippet", "").strip()
        trigger = _infer_trigger(text, orig_type, corr_type)
        if not trigger:
            continue

        matched = next((p for p in patterns if p["trigger"] == trigger), None)
        if matched:
            matched["observed_count"] += 1
            matched["confidence"] = min(0.95, matched["confidence"] + 0.05)
            matched["last_seen"] = _now()
        else:
            patterns.append({
                "trigger": trigger,
                "original_type": orig_type,
                "inferred_type": corr_type,
                "confidence": 0.65,
                "observed_count": 1,
                "first_seen": _now(),
                "last_seen": _now(),
            })

    patterns = sorted(patterns, key=lambda p: p["confidence"], reverse=True)[:MAX_PATTERNS]
    prefs["learned_patterns"] = patterns
    return prefs


def _infer_trigger(text: str, orig_type: str, corr_type: str) -> str | None:
    if not text:
        return None
    text_lower = text.lower().strip()
    if text and text[0].isupper() and len(text.split()) <= 6 and corr_type.startswith("heading"):
        return f"short_title_case_to_{corr_type}"
    if text_lower.startswith(tuple("0123456789")) and "." in text[:4] and corr_type.startswith("heading"):
        return "numbered_line_to_heading"
    if text_lower.startswith(("•", "-", "*", "–")) and corr_type == "bullet_list":
        return "bullet_marker_to_bullet_list"
    if orig_type == "paragraph" and corr_type == "heading":
        return "paragraph_promoted_to_heading"
    if orig_type == "heading" and corr_type == "paragraph":
        return "heading_demoted_to_paragraph"
    return None


def reinforce_pattern(prefs: dict, trigger: str, was_correct: bool) -> dict:
    patterns = prefs.get("learned_patterns", [])
    for p in patterns:
        if p["trigger"] == trigger:
            if was_correct:
                p["confidence"] = min(0.95, p["confidence"] + 0.05)
                p["observed_count"] += 1
            else:
                p["confidence"] = max(0.0, p["confidence"] - 0.10)
    prefs["learned_patterns"] = [p for p in patterns if p["confidence"] >= 0.30]
    return prefs


def add_feedback(prefs: dict, rating: str, comment: str, document_type: str, confidence_score: float) -> dict:
    entry = {
        "timestamp": _now(),
        "rating": rating,
        "comment": comment,
        "document_type": document_type,
        "confidence_score": confidence_score,
    }
    prefs.setdefault("feedback_history", []).append(entry)
    prefs["feedback_history"] = prefs["feedback_history"][-50:]
    return prefs


def log_agent_decision(decision: dict, image_name: str, path: str = LOG_PATH) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "r", encoding="utf-8") as f:
            log = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        log = {"entries": []}

    entry = {
        "timestamp": _now(),
        "image_name": image_name,
        "document_type": decision.get("document_type", "unknown"),
        "confidence_score": decision.get("confidence_score", 0.0),
        "reasoning": decision.get("reasoning", ""),
        "model_used": decision.get("model_used", ""),
        "tokens_used": decision.get("tokens_used", 0),
        "processing_time_ms": decision.get("processing_time_ms", 0),
        "block_count": len(decision.get("blocks", [])),
        "warnings": decision.get("warnings", []),
        "user_corrections_applied": len(st.session_state.get("corrections", [])),
    }
    log["entries"].append(entry)
    log["entries"] = log["entries"][-MAX_LOG_ENTRIES:]

    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)
    os.replace(tmp_path, path)


def load_log(path: str = LOG_PATH) -> list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f).get("entries", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []
