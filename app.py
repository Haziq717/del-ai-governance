"""Streamlit handles input and display. agent.py handles the assessment."""
import json
import os
from pathlib import Path

import streamlit as st

from agent import POLICIES, STATUSES, assess
from audit import record_event

BASE = Path(__file__).resolve().parent
scenarios = json.loads((BASE / 'scenarios.json').read_text())
st.set_page_config(page_title='Security & Compliance Analyst', layout='wide')
st.title('Security & Compliance Analyst')
st.caption('Acme Financial Services • Initial assessment • Human review required')
st.warning('Fictional scenarios only. Submitted text is sent to Google Gemini. Do not enter real personal or confidential information.')
model = st.sidebar.text_input('Gemini model', value=os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'))
st.sidebar.caption('Choose a model enabled for your AI Studio project. Free-tier quotas vary.')
choice = st.selectbox('Choose a scenario', ['Custom scenario', *scenarios])
scenario = st.text_area('Describe the proposed AI application', value=scenarios.get(choice, ''),
                        height=220, max_chars=10000, key=choice)
consent = st.checkbox('This is fictional data and I agree to send it to the configured AI provider.')
with st.expander('Governance requirements'):
    for policy in POLICIES:
        st.text(f"{policy['id']}: {policy['requirement']}")

if st.button('Assess scenario', type='primary'):
    st.session_state.pop('assessment', None)
    if not scenario.strip():
        st.error('Enter a scenario first.')
    elif not consent:
        st.error('Confirm fictional data before submitting.')
    elif not model.strip():
        st.error('Enter a model name.')
    else:
        try:
            with st.spinner('Retrieving requirements and assessing evidence…'):
                result, trace = assess(scenario, model.strip())
            try:
                metadata = record_event(model, 'validated', [t['tool'] for t in trace])
            except Exception:
                metadata = {'logging': 'failed'}
                st.warning('Assessment completed, but the audit metadata could not be saved.')
            st.session_state.assessment = {'input': scenario, 'result': result, 'trace': trace, 'metadata': metadata}
        except Exception as error:
            # Show only our controlled messages, never raw provider exceptions.
            if isinstance(error, (ValueError, RuntimeError)) and not isinstance(error, json.JSONDecodeError):
                st.error(str(error))
            else:
                st.error('Assessment could not be completed or validated. Check connectivity and retry.')
            try:
                record_event(model, 'failed', [])
            except Exception:
                st.warning('Failure metadata could not be logged.')

saved = st.session_state.get('assessment')
if saved and saved['input'] == scenario:
    result = saved['result']
    st.subheader('Assessment')
    st.text(result['summary'])
    st.info('Initial assessment only. This is not deployment approval.')
    st.write('Additional risk review recommended:', result['review_recommended'])
    st.text(result['review_reason'])
    columns = st.columns(4)
    for column, status in zip(columns, STATUSES):
        column.metric(status, sum(f['status'] == status for f in result['findings']))
    for finding in sorted(result['findings'], key=lambda f: f['policy_id']):
        with st.expander(f"{finding['policy_id']} — {finding['status']}", expanded=True):
            st.text('Evidence: ' + (finding['evidence'] or 'Not provided in scenario.'))
            st.text('Explanation: ' + finding['explanation'])
            st.text('Action: ' + finding['action'])
    with st.expander('Execution trace and assessment metadata'):
        st.json(saved['metadata'])
        st.json(saved['trace'])
    st.download_button('Download assessment JSON', json.dumps(saved, indent=2),
                       file_name='assessment.json', mime='application/json')
