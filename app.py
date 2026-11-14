import json
from pathlib import Path

import streamlit as st

# Resolve data files relative to this script, regardless of the launch directory.
BASE_DIR = Path(__file__).resolve().parent
policies = json.loads((BASE_DIR / "policies.json").read_text())
scenarios = json.loads((BASE_DIR / "scenarios.json").read_text())

st.set_page_config(page_title="Security & Compliance Analyst", layout="wide")
st.title("Security & Compliance Analyst")
st.caption("Initial assessment for Acme Financial Services. Human review is required.")
st.warning("Use fictional scenarios only. Do not enter real confidential or personal information.")

choice = st.selectbox("Choose a scenario", ["Custom scenario", *scenarios])
# A separate widget key retains edits for each selected example.
scenario = st.text_area(
    "Describe the proposed AI application",
    value=scenarios.get(choice, ""),
    height=230,
    max_chars=10000,
    key=choice,
)

with st.expander("View the eight assessment requirements"):
    for policy in policies:
        st.write(f"**{policy['id']}** — {policy['requirement']}")

if st.button("Validate input", type="primary"):
    if not scenario.strip():
        st.error("Enter a scenario before continuing.")
    else:
        st.success("Input accepted. GPT assessment will be added in the next step.")
        st.info("No information has been sent to an AI service.")
