"""
brief_ui.py
-----------
Drop-in Streamlit UI component for the LLM analyst brief.

Imports the brief generator and renders the button, gating controls,
and the four-section tabbed output. Styling matches the Readout design
system (light/clinical, teal accent, Inter typography).
"""

import streamlit as st
from generate_brief import generate_analyst_brief


def render_brief_section(df_filtered, filters: dict):
    """
    Renders the Generate Brief button and tabbed brief output.

    Args:
        df_filtered: The filtered DataFrame used to render charts above
        filters: Dict of active filter values from the sidebar
    """

    # ── Constants ──────────────────────────────────────────────────────────
    SESSION_LIMIT = 3       # max brief generations per user session
    DATASET_ROW_CAP = 500   # rows passed to context builder

    # ── Section header (matches existing .section-label pattern) ───────────
    st.markdown(
        "<div class='section-label'>AI Analyst Brief</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <p style="color:#64748b; font-size:0.82rem; line-height:1.55;
                  margin-top:-0.5rem; margin-bottom:1rem; max-width:680px;">
            A plain-language competitive intelligence brief synthesized from the filtered dataset above.
            Powered by Claude · Synthesis takes 5–10 seconds.
        </p>
        """,
        unsafe_allow_html=True,
    )

    # ── Kill switch ────────────────────────────────────────────────────────
    if not st.secrets.get("BRIEF_ENABLED", True):
        st.info("Brief generation is temporarily unavailable.")
        return

    # ── No data guard ──────────────────────────────────────────────────────
    if df_filtered is None or len(df_filtered) == 0:
        st.info("Apply filters above to enable brief generation.")
        return

    # ── Session-based rate limit ───────────────────────────────────────────
    if "brief_count" not in st.session_state:
        st.session_state.brief_count = 0

    remaining = SESSION_LIMIT - st.session_state.brief_count

    if remaining <= 0:
        st.warning(
            f"You've used all {SESSION_LIMIT} brief generations for this session. "
            "Refresh the page to start a new session."
        )
        return

    # ── Button + remaining-count caption, on one row ──────────────────────
    btn_col, count_col = st.columns([1, 4])
    with btn_col:
        clicked = st.button(
            "Generate Brief",
            type="primary",
            help="Calls the Claude API to synthesize a competitive intelligence brief from the current filtered view.",
            use_container_width=True,
        )
    with count_col:
        if st.session_state.brief_count > 0:
            st.markdown(
                f"<div style='padding-top:0.55rem; color:#64748b; "
                f"font-size:0.78rem; font-family:IBM Plex Mono, monospace;'>"
                f"{remaining} of {SESSION_LIMIT} remaining this session"
                f"</div>",
                unsafe_allow_html=True,
            )

    if not clicked:
        return

    # ── Run the brief ──────────────────────────────────────────────────────
    df_for_brief = (
        df_filtered.sample(n=DATASET_ROW_CAP, random_state=42)
        if len(df_filtered) > DATASET_ROW_CAP
        else df_filtered
    )

    with st.spinner("Synthesizing analyst brief…"):
        api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
        brief = generate_analyst_brief(df_for_brief, filters, api_key=api_key)

    st.session_state.brief_count += 1

    if brief.get("error"):
        st.error(brief["error"])
        return

    # ── Tabbed output ──────────────────────────────────────────────────────
    card_style = (
        "background:#ffffff; border:1px solid #d1dae2; border-radius:8px; "
        "padding:1.25rem 1.5rem; color:#1a2332; line-height:1.65; "
        "font-size:0.9rem; margin-top:0.75rem;"
    )

    takeaway_style = (
        "background:#f0fdfa; border-left:3px solid #0d9488; "
        "border-radius:0 8px 8px 0; padding:1.25rem 1.5rem; "
        "color:#1a2332; line-height:1.7; font-size:0.93rem; margin-top:0.75rem;"
    )

    tab_summary, tab_competitive, tab_signals, tab_takeaway = st.tabs([
        "Pipeline Summary",
        "Competitive Landscape",
        "Key Signals",
        "Takeaway",
    ])

    with tab_summary:
        st.markdown(
            f"<div style='{card_style}'>{brief['pipeline_summary']}</div>",
            unsafe_allow_html=True,
        )

    with tab_competitive:
        st.markdown(
            f"<div style='{card_style}'>{brief['competitive_landscape']}</div>",
            unsafe_allow_html=True,
        )

    with tab_signals:
        st.markdown(
            f"<div style='{card_style}'>{brief['key_signals']}</div>",
            unsafe_allow_html=True,
        )

    with tab_takeaway:
        st.markdown(
            f"<div style='{takeaway_style}'>{brief['takeaway']}</div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='font-size:0.7rem; color:#9ca3af; "
        "font-family:IBM Plex Mono, monospace; margin-top:0.75rem;'>"
        "Generated by Claude (claude-sonnet-4-6) from filtered ClinicalTrials.gov + openFDA data. "
        "Not for clinical decision-making."
        "</div>",
        unsafe_allow_html=True,
    )
