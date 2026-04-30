import hashlib
import io
from pathlib import Path

import streamlit as st

from agents import analysis_agent, docx_agent, memory_agent, ocr_agent

st.set_page_config(
    page_title="DocAgent — Intelligent OCR",
    page_icon="🤖",
    layout="wide",
)

memory_agent.init_session_state()


def _run_pipeline(image_bytes: bytes, image_name: str) -> dict:
    prefs = memory_agent.load_preferences()

    with st.status("🤖 Agent pipeline running…", expanded=True) as status:

        # Agent 1: OCR
        st.write("🔍 **OCR Agent** — preprocessing image and extracting text…")
        try:
            ocr_result = ocr_agent.run_enhanced_ocr(image_bytes, image_name)
        except ocr_agent.OCRError as e:
            status.update(label="❌ OCR failed", state="error")
            return {"error": str(e)}

        engine = ocr_result.get("ocr_engine", "tesseract")
        engine_label = "🔭 Groq Vision" if engine == "vision" else "🔤 Tesseract"
        st.write(
            f"   ✅ Extracted **{ocr_result['word_count']} words** "
            f"with **{ocr_result['confidence']}% confidence** via {engine_label}"
        )
        if engine == "vision":
            st.write("   ℹ️ _Tesseract confidence was low — Groq Vision used as fallback._")

        if ocr_result["word_count"] == 0:
            status.update(label="⚠️ No text found in image", state="error")
            return {"error": "No text detected. Try a clearer scan.", "ocr": ocr_result}

        # Agent 2: Analysis
        st.write("🧠 **Analysis Agent** — reasoning about document structure…")
        analysis_result = analysis_agent.analyze_document(ocr_result, prefs, [])

        if analysis_result["status"] == "error":
            st.write("   ⚠️ AI analysis failed — using raw OCR text as fallback.")
            docx_buf = docx_agent.build_passthrough_docx(ocr_result["raw_text"])
            status.update(label="✅ Done (raw OCR — AI unavailable)", state="complete")
            return {"ocr": ocr_result, "analysis": None, "docx": docx_buf, "fallback": True}

        block_count = len(analysis_result.get("blocks", []))
        doc_type = analysis_result.get("document_type", "unknown")
        conf = analysis_result.get("confidence_score", 0)
        st.write(
            f"   ✅ Detected **{doc_type}** document · "
            f"**{block_count} blocks** · confidence **{conf:.0%}**"
        )
        st.write(f"   💬 _{analysis_result.get('reasoning', '')}_")

        # Agent 3: DOCX
        st.write("📝 **DOCX Agent** — generating formatted Word document…")
        docx_buf = docx_agent.build_docx(analysis_result)
        st.write("   ✅ Document ready for download.")

        # Memory: log and save
        memory_agent.log_agent_decision(analysis_result, image_name)
        prefs["session_count"] = prefs.get("session_count", 0) + 1
        memory_agent.save_preferences(prefs)

        status.update(label="✅ Pipeline complete!", state="complete")

    return {"ocr": ocr_result, "analysis": analysis_result, "docx": docx_buf, "fallback": False}


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🤖 DocAgent")
    st.caption("Agentic Image-to-Word System")
    st.divider()

    prefs = memory_agent.load_preferences()
    st.markdown(f"**Sessions run:** {prefs.get('session_count', 0)}")
    st.markdown(f"**Patterns learned:** {len(prefs.get('learned_patterns', []))}")

    st.divider()
    log_entries = memory_agent.load_log()
    if log_entries:
        with st.expander(f"📋 Agent Log ({len(log_entries)} runs)"):
            for entry in reversed(log_entries[-5:]):
                ts = entry.get("timestamp", "")[:16].replace("T", " ")
                conf = entry.get("confidence_score", 0)
                st.markdown(
                    f"**{ts}**  \n"
                    f"`{entry.get('document_type', '?')}` · "
                    f"{conf:.0%} · {entry.get('block_count', 0)} blocks"
                )
    else:
        st.caption("No runs yet.")

# ── Main ──────────────────────────────────────────────────────────────────────
st.title("🤖 DocAgent — Intelligent Image-to-Word")
st.markdown(
    "Upload a scanned document image. "
    "Three specialised agents will automatically extract, analyse, and format it into a Word document."
)

uploaded_file = st.file_uploader(
    "Choose an image (JPG / PNG)",
    type=["jpg", "jpeg", "png"],
    label_visibility="visible",
)

if uploaded_file is not None:
    image_bytes = uploaded_file.read()
    image_hash = hashlib.md5(image_bytes).hexdigest()

    # Invalidate cached result when a new image is uploaded
    if st.session_state.get("_last_hash") != image_hash:
        st.session_state["_last_hash"] = image_hash
        st.session_state["_pipeline_result"] = None

    col_img, col_out = st.columns([1, 2])

    with col_img:
        st.image(image_bytes, caption=uploaded_file.name, width="stretch")

    with col_out:
        # Run pipeline automatically (once per image)
        if st.session_state.get("_pipeline_result") is None:
            result = _run_pipeline(image_bytes, uploaded_file.name)
            st.session_state["_pipeline_result"] = result
        else:
            result = st.session_state["_pipeline_result"]

        if "error" in result:
            st.error(result["error"])
        else:
            ocr = result["ocr"]
            analysis = result.get("analysis")
            docx_buf: io.BytesIO = result["docx"]

            # ── Results ───────────────────────────────────────────────────
            st.markdown("---")

            # Metrics row
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Words extracted", ocr["word_count"])
            engine = ocr.get("ocr_engine", "tesseract")
            m2.metric("OCR engine", "🔭 Vision" if engine == "vision" else "🔤 Tesseract",
                      help=ocr.get("preprocessing_applied", ""))
            if analysis:
                m3.metric("Document type", analysis.get("document_type", "?"))
                conf = analysis.get("confidence_score", 0)
                badge = "🟢" if conf >= 0.85 else ("🟡" if conf >= 0.70 else "🔴")
                m4.metric("AI confidence", f"{badge} {conf:.0%}")
            else:
                m3.metric("Mode", "Raw OCR")
                m4.metric("AI", "bypassed")

            # Download
            stem = Path(uploaded_file.name).stem
            suffix = "_raw" if result.get("fallback") else "_agent"
            st.download_button(
                label="📥 Download Word Document (.docx)",
                data=docx_buf,
                file_name=f"{stem}{suffix}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary",
                use_container_width=True,
            )

            # Extracted text preview
            with st.expander("📄 Extracted text preview"):
                st.text(ocr["raw_text"])

            # Block details
            if analysis and analysis.get("blocks"):
                with st.expander(f"🧠 AI formatting decisions ({len(analysis['blocks'])} blocks)"):
                    for b in analysis["blocks"]:
                        conf_icon = "🟢" if b["confidence"] >= 0.85 else ("🟡" if b["confidence"] >= 0.70 else "🔴")
                        st.markdown(
                            f"{conf_icon} **{b['block_type']}** "
                            f"(align: {b['alignment']}, bold: {b['bold']}, italic: {b['italic']})  \n"
                            f"> {b['text'][:100]}{'…' if len(b['text']) > 100 else ''}  \n"
                            f"_↳ {b['reasoning']}_"
                        )

            if analysis and analysis.get("warnings"):
                with st.expander("⚠️ Agent warnings"):
                    for w in analysis["warnings"]:
                        st.warning(str(w))

            # Feedback
            st.markdown("---")
            st.caption("Was the output useful?")
            fb_col1, fb_col2, _ = st.columns([1, 1, 4])
            with fb_col1:
                if st.button("👍 Yes"):
                    p = memory_agent.load_preferences()
                    p = memory_agent.add_feedback(
                        p, "positive", "",
                        analysis.get("document_type", "unknown") if analysis else "raw",
                        analysis.get("confidence_score", 0) if analysis else 0,
                    )
                    memory_agent.save_preferences(p)
                    st.toast("Thanks for the feedback!")
            with fb_col2:
                if st.button("👎 No"):
                    p = memory_agent.load_preferences()
                    p = memory_agent.add_feedback(
                        p, "negative", "",
                        analysis.get("document_type", "unknown") if analysis else "raw",
                        analysis.get("confidence_score", 0) if analysis else 0,
                    )
                    memory_agent.save_preferences(p)
                    st.toast("Noted — will improve.")
