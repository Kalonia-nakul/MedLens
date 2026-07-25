"""MedLens - a local, AI-assisted first read of a patient report."""

import streamlit as st

from medlens import config
from medlens.ollama_client import MedLensError, analyze_report
from medlens.prompts import SYSTEM_PROMPT, build_user_prompt
from medlens.report_parser import extract_text

st.set_page_config(page_title="MedLens", page_icon="🩺", layout="wide")

SEVERITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def render_disclaimer() -> None:
    st.warning(
        "**MedLens is not a doctor.** It gives a plain-language first read "
        "of a report to help you prepare for a conversation with a "
        "clinician, and it can misread or misunderstand your report. "
        "For anything urgent, contact a healthcare professional or "
        "emergency services immediately.",
        icon="⚠️",
    )


def render_result(result: dict) -> None:
    if result.get("_parse_error"):
        st.info(
            "The model's reply didn't come back as clean structured data - "
            "showing it as-is below:"
        )
        st.write(result.get("summary", ""))
        st.caption(result.get("disclaimer", ""))
        return

    st.subheader("Summary")
    st.write(result.get("summary", ""))

    risk_flags = result.get("risk_flags") or []
    if risk_flags:
        st.subheader("Risk flags")
        for flag in sorted(
            risk_flags, key=lambda f: SEVERITY_ORDER.get(f.get("severity", "low"), 3)
        ):
            icon = SEVERITY_ICON.get(flag.get("severity", "low"), "⚪")
            with st.container(border=True):
                st.markdown(
                    f"{icon} **{flag.get('item', '')}** — "
                    f"{flag.get('severity', '').upper()}"
                )
                st.caption(flag.get("explanation", ""))

    key_findings = result.get("key_findings") or []
    if key_findings:
        st.subheader("Key findings")
        for kf in key_findings:
            with st.expander(kf.get("finding", "Finding")):
                st.write(kf.get("detail", ""))

    foresight = result.get("foresight") or []
    if foresight:
        st.subheader("Foresight — things to watch")
        for item in foresight:
            with st.container(border=True):
                st.markdown(
                    f"**{item.get('insight', '')}**  \n"
                    f"*Timeframe: {item.get('timeframe', 'unspecified')}*"
                )
                st.caption(item.get("rationale", ""))

    questions = result.get("recommended_questions") or []
    if questions:
        st.subheader("Questions to bring to your doctor")
        for q in questions:
            st.markdown(f"- {q}")

    lifestyle = result.get("lifestyle_suggestions") or []
    if lifestyle:
        st.subheader("General lifestyle notes")
        for tip in lifestyle:
            st.markdown(f"- {tip}")

    st.divider()
    st.caption(result.get("disclaimer", ""))


def main() -> None:
    st.title("🩺 MedLens")
    st.caption("A local, private, Ollama-powered first read of your patient report.")
    render_disclaimer()

    with st.sidebar:
        st.header("Settings")
        model = st.selectbox(
            "Ollama model",
            config.AVAILABLE_MODELS,
            index=config.AVAILABLE_MODELS.index(config.DEFAULT_MODEL),
        )
        temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.1)
        st.caption(f"Make sure it's pulled locally:\n\n`ollama pull {model}`")
        st.divider()
        st.caption(f"Ollama host: `{config.OLLAMA_HOST}`")
        st.caption("Everything runs on your machine - no report data leaves it.")

    tab_upload, tab_paste = st.tabs(["Upload file", "Paste text"])
    report_text = ""

    with tab_upload:
        uploaded = st.file_uploader("Upload a report (PDF or TXT)", type=["pdf", "txt", "md"])
        if uploaded is not None:
            try:
                report_text = extract_text(uploaded)
                st.success(f"Extracted {len(report_text)} characters from {uploaded.name}.")
                with st.expander("Preview extracted text"):
                    st.text(report_text[:3000])
            except ValueError as exc:
                st.error(str(exc))

    with tab_paste:
        pasted = st.text_area("Paste the report text here", height=250)
        if pasted.strip():
            report_text = pasted

    patient_context = st.text_input(
        "Optional: anything else worth mentioning (symptoms, history, medications)?"
    )

    analyze_clicked = st.button(
        "Analyze report", type="primary", disabled=not report_text.strip()
    )

    if analyze_clicked:
        with st.spinner(f"Running {model} locally - this can take a minute on CPU..."):
            try:
                user_prompt = build_user_prompt(report_text, patient_context)
                result = analyze_report(
                    SYSTEM_PROMPT, user_prompt, model=model, temperature=temperature
                )
                render_result(result)
            except MedLensError as exc:
                st.error(str(exc))


if __name__ == "__main__":
    main()
