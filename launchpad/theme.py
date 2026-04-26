"""Streamlit page configuration and shared CSS."""

from __future__ import annotations

import streamlit as st


MOBILE_CSS = """
<style>
:root {
  --lp-bg: #f4f7fb;
  --lp-card: rgba(255, 255, 255, 0.92);
  --lp-line: rgba(15, 23, 42, 0.10);
  --lp-line-strong: rgba(15, 23, 42, 0.18);
  --lp-ink: #0f172a;
  --lp-muted: #5b6475;
  --lp-accent: #0f766e;
  --lp-glow: rgba(15, 118, 110, 0.18);
  --lp-mono: "SFMono-Regular", "Roboto Mono", Consolas, "Liberation Mono", Menlo, monospace;
  --lp-sans: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
}
html, body, [class*="css"] {font-family: var(--lp-sans);}
body, .stApp {
  background:
    radial-gradient(circle at top left, rgba(15, 118, 110, 0.10), transparent 28%),
    radial-gradient(circle at top right, rgba(234, 179, 8, 0.10), transparent 24%),
    linear-gradient(180deg, #fbfdff 0%, var(--lp-bg) 100%);
  color: var(--lp-ink);
  color-scheme: light;
}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {visibility: hidden;}
div[data-testid="stToolbar"] {visibility: hidden;}
.block-container {padding-top: 1rem; padding-bottom: 4rem; max-width: 720px;}
button {min-height: 48px; font-size: 1.05rem;}
div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea {
  font-size: 1.05rem !important;
  min-height: 44px;
}
[data-testid="stTabs"] button {min-height: 44px;}
div[data-testid="stTabs"] [role="tablist"] {
  gap: 0.5rem;
}
div[data-testid="stTabs"] button {
  border-radius: 12px 12px 0 0 !important;
  background: transparent !important;
  color: var(--lp-muted) !important;
  box-shadow: none !important;
}
div[data-testid="stTabs"] button:hover {
  color: var(--lp-ink) !important;
  background: rgba(255, 255, 255, 0.55) !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
  color: var(--lp-accent) !important;
  background: rgba(15, 118, 110, 0.08) !important;
}
div[data-testid="stTabs"] button * {
  color: inherit !important;
}
div[data-testid="column"] .stButton > button {white-space: nowrap;}
div.stButton > button,
div.stFormSubmitButton > button,
div[data-testid="stFormSubmitButton"] > button {
  border-radius: 999px;
  border: 1px solid var(--lp-line-strong);
  background: linear-gradient(180deg, #ffffff 0%, #eef3f9 100%);
  color: var(--lp-ink) !important;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 700;
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
}
div.stButton > button *,
div.stFormSubmitButton > button *,
div[data-testid="stFormSubmitButton"] > button * {
  color: inherit !important;
}
div.stButton > button:hover,
div.stFormSubmitButton > button:hover,
div[data-testid="stFormSubmitButton"] > button:hover {
  border-color: rgba(15, 118, 110, 0.45);
  box-shadow: 0 10px 24px rgba(15, 118, 110, 0.16);
}
div.stButton > button[kind="primary"],
div.stFormSubmitButton > button[kind="primary"],
div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
  background: linear-gradient(180deg, #0f766e 0%, #115e59 100%) !important;
  color: #ffffff !important;
  border-color: rgba(15, 118, 110, 0.85) !important;
}
div.stButton > button[kind="primary"]:hover,
div.stFormSubmitButton > button[kind="primary"]:hover,
div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
  border-color: rgba(15, 118, 110, 1) !important;
  box-shadow: 0 12px 26px rgba(15, 118, 110, 0.24) !important;
}
div[data-testid="stSegmentedControl"] {
  background: transparent !important;
  color-scheme: light !important;
  forced-color-adjust: none;
}
div[data-testid="stSegmentedControl"] [data-baseweb="button-group"] {
  gap: 0.4rem;
  background: transparent !important;
  box-shadow: none !important;
  color-scheme: light !important;
}
div[data-testid="stSegmentedControl"] [data-baseweb="button-group"] button {
  border-radius: 999px !important;
  border: 1px solid transparent !important;
  background: rgba(255, 255, 255, 0.82) !important;
  color: var(--lp-ink) !important;
  -webkit-text-fill-color: var(--lp-ink) !important;
  box-shadow: none !important;
  text-transform: none !important;
  letter-spacing: 0 !important;
  font-weight: 600 !important;
  opacity: 1 !important;
  filter: none !important;
  color-scheme: light !important;
}
div[data-testid="stSegmentedControl"] [data-baseweb="button-group"] button:hover {
  border-color: var(--lp-line-strong) !important;
  background: rgba(255, 255, 255, 0.96) !important;
}
div[data-testid="stSegmentedControl"] [data-baseweb="button-group"] button[aria-selected="true"],
div[data-testid="stSegmentedControl"] [data-baseweb="button-group"] button[aria-pressed="true"],
div[data-testid="stSegmentedControl"] [data-baseweb="button-group"] button[data-active="true"] {
  background: linear-gradient(180deg, #0f172a 0%, #111827 100%) !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
  border-color: rgba(15, 23, 42, 0.85) !important;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.14) !important;
}
div[data-testid="stSegmentedControl"] [data-baseweb="button-group"] button *,
div[data-testid="stSegmentedControl"] [data-baseweb="button-group"] [role="radiogroup"] *,
div[data-testid="stSegmentedControl"] [data-baseweb="button-group"] [role="group"] * {
  color: inherit !important;
  -webkit-text-fill-color: inherit !important;
  opacity: 1 !important;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius: 20px;
  border: 1px solid rgba(15, 118, 110, 0.18) !important;
  background: var(--lp-card);
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.65) inset,
    0 0 0 1px rgba(15, 118, 110, 0.04),
    0 18px 40px rgba(15, 23, 42, 0.06),
    0 0 28px var(--lp-glow);
}
div[data-testid="stMetric"] {
  background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(244,247,251,0.98) 100%);
  border: 1px solid var(--lp-line);
  border-radius: 18px;
  padding: 0.9rem 1rem;
}
div[data-testid="stMetricLabel"] {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--lp-muted) !important;
}
div[data-testid="stMetricValue"] {
  font-family: var(--lp-mono);
  letter-spacing: 0.03em;
  color: var(--lp-ink) !important;
}
div[data-testid="stMetricLabel"] *,
div[data-testid="stMetricValue"] *,
div[data-testid="stMetricDelta"] * {
  color: inherit !important;
  background: transparent !important;
}
div[data-testid="stMetricDelta"] {
  color: var(--lp-muted) !important;
}
div[data-testid="stExpander"] {
  border: 1px solid var(--lp-line) !important;
  border-radius: 18px !important;
  background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(244,247,251,0.96) 100%) !important;
  overflow: hidden;
}
div[data-testid="stExpander"] details {
  background: transparent !important;
}
div[data-testid="stExpander"] summary {
  background: transparent !important;
  color: var(--lp-ink) !important;
}
div[data-testid="stExpander"] summary:hover {
  background: rgba(15, 118, 110, 0.06) !important;
}
div[data-testid="stExpander"] summary * {
  color: var(--lp-ink) !important;
  fill: var(--lp-ink) !important;
}
div[data-testid="stExpander"] div[role="region"] {
  color: var(--lp-ink) !important;
}
div[data-testid="stExpander"] div[role="region"] * {
  color: inherit !important;
}
code, .admin-mono {font-family: var(--lp-mono);}
.admin-section-kicker {
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--lp-accent);
  margin-bottom: 0.35rem;
}
.admin-card-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--lp-ink);
  line-height: 1.25;
}
.admin-card-subtitle {
  font-size: 0.9rem;
  color: var(--lp-muted);
  margin-top: 0.15rem;
}
.admin-rank {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 3rem;
  border-radius: 16px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(236,242,248,0.98) 100%);
  font-size: 1.5rem;
  font-weight: 800;
}
.admin-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #ffffff;
  margin: 0.18rem 0.28rem 0.18rem 0;
}
.admin-mini-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.22rem 0.55rem;
  border-radius: 999px;
  margin: 0.18rem 0.3rem 0 0;
  background: rgba(15, 118, 110, 0.08);
  border: 1px solid rgba(15, 118, 110, 0.10);
  color: var(--lp-ink);
  font-size: 0.76rem;
}
.admin-progress-label,
.admin-quota-label {
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--lp-muted);
  margin-bottom: 0.35rem;
}
.admin-progress-track,
.admin-quota-track {
  width: 100%;
  height: 0.7rem;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.08);
  overflow: hidden;
}
.admin-progress-fill,
.admin-quota-fill {
  height: 100%;
  border-radius: 999px;
}
.admin-progress-value,
.admin-quota-value,
.admin-microcopy {
  margin-top: 0.4rem;
  font-size: 0.86rem;
  color: var(--lp-muted);
}
.admin-empty {
  padding: 0.3rem 0;
  color: var(--lp-muted);
}
@media (max-width: 760px) {
  .block-container {padding-left: 0.85rem; padding-right: 0.85rem; max-width: 100%;}
  div[data-testid="stHorizontalBlock"] {flex-direction: column; gap: 0.75rem;}
  div[data-testid="column"] {width: 100% !important; flex: 1 1 100% !important;}
}
</style>
"""


def configure_page() -> None:
    st.set_page_config(
        page_title="Launchpad",
        layout="centered",
        initial_sidebar_state="expanded",
    )


def apply_theme() -> None:
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)

