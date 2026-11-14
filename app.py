"""A small dashboard. Assessment logic stays in agent.py."""
import json
import os
from pathlib import Path

import streamlit as st

from agent import POLICIES, STATUSES, assess
from audit import record_event

BASE = Path(__file__).resolve().parent
scenarios = json.loads((BASE / 'scenarios.json').read_text())
st.set_page_config(page_title='AI Governance Analyst', page_icon='🛡️', layout='wide')
# Static styling only. Model output is always rendered as plain text.
st.markdown('''<style>
.stApp {background: #0b1120;}
.block-container {max-width: 1280px; padding-top: 2rem;}
[data-testid="stMetric"] {background: #152239; padding: 18px; border-radius: 12px;}
div.stButton > button[kind="primary"] {background: #2563eb; border: none;}
</style>''', unsafe_allow_html=True)
st.title('AI Governance Analyst')
st.caption('Acme Financial Services  /  Security & Compliance Workspace')
st.write('Assess a proposed AI application, inspect the evidence, and identify what needs review.')

with st.sidebar:
    st.subheader('Assessment settings')
    st.caption('Provider: Groq')
    model = st.text_input('Model', value=os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b'))
    if os.getenv('GROQ_API_KEY'):
        st.success('API key detected')
    else:
        st.error('GROQ_API_KEY is missing')
    st.caption('Key detection does not verify API access. Account quotas apply.')
    st.divider()
    st.write('8 governance requirements')
    st.write('2 allowed read-only tools')
    st.write('2 API calls per assessment')
    st.info('Initial assessment only. Human review is required.')


def choose_example(name):
    st.session_state.scenario_choice = name
    st.session_state.pop(name, None)
    st.session_state.pop('assessment', None)


st.subheader('1. Choose a use case')
descriptions = ['Customer data, suggested responses, human review.',
                'Security alerts, internal logs, analyst oversight.',
                'HR records, promotion recommendations, decision risk.']
for column, (name, description) in zip(st.columns(3), zip(scenarios, descriptions)):
    with column.container(border=True):
        st.markdown(f'**{name}**')
        st.caption(description)
        st.button('Load scenario', key='load_' + name, on_click=choose_example, args=(name,), use_container_width=True)

choice = st.selectbox('Choose a scenario', ['Custom scenario', *scenarios], key='scenario_choice')
scenario = st.text_area('Describe the proposed AI application', value=scenarios.get(choice, ''),
                        height=180, max_chars=10000, key=choice)
st.caption(f'{len(scenario):,} / 10,000 characters • Add facts about ownership, data, oversight, and controls if known.')
st.warning('Fictional data only. Your scenario is sent to Groq. Do not enter real personal or confidential information.')
consent = st.checkbox('This is fictional data and I agree to send it to the configured AI provider.')

if st.button('Assess scenario', type='primary', use_container_width=True):
    st.session_state.pop('assessment', None)
    if not scenario.strip():
        st.error('Enter a scenario first.')
    elif not consent:
        st.error('Confirm fictional data before submitting.')
    elif not model.strip():
        st.error('Enter a model name.')
    else:
        try:
            with st.status('Assessing scenario…', expanded=True) as status:
                try:
                    result, trace = assess(scenario, model.strip(), progress=st.write)
                except Exception:
                    status.update(label='Assessment stopped', state='error', expanded=True)
                    raise
                status.update(label='Assessment complete', state='complete', expanded=False)
            try:
                metadata = record_event(model, 'validated', [t['tool'] for t in trace])
            except Exception:
                metadata = {'logging': 'failed'}
                st.warning('Assessment completed, but audit metadata could not be saved.')
            st.session_state.assessment = {'input': scenario, 'result': result, 'trace': trace,
                                           'metadata': {**metadata, 'provider': 'Groq'}}
        except Exception as error:
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
    st.divider()
    st.subheader('2. Assessment overview')
    st.text(result['summary'])
    if result['review_recommended']:
        st.warning('Additional risk review recommended')
    else:
        st.info('No additional risk review recommended by the model. This is not deployment approval.')
    st.text(result['review_reason'])
    for column, status_name in zip(st.columns(4), STATUSES):
        column.metric(status_name, sum(f['status'] == status_name for f in result['findings']))

    findings_tab, actions_tab, trace_tab = st.tabs(['Policy findings', 'Action list', 'Execution trace'])
    with findings_tab:
        selected = st.multiselect('Filter findings by status', STATUSES, default=STATUSES)
        visible = [f for f in result['findings'] if f['status'] in selected]
        if not visible:
            st.info('No findings match this filter.')
        for finding in sorted(visible, key=lambda f: f['policy_id']):
            with st.expander(f"{finding['policy_id']} — {finding['status']}", expanded=True):
                policy = next(p for p in POLICIES if p['id'] == finding['policy_id'])
                st.caption(policy['requirement'])
                st.text('Evidence: ' + (finding['evidence'] or 'Not provided in scenario.'))
                st.text('Explanation: ' + finding['explanation'])
                st.text('Action: ' + finding['action'])
    with actions_tab:
        for finding in result['findings']:
            if finding['status'] not in ['Met', 'Not applicable']:
                with st.container(border=True):
                    st.write(finding['policy_id'] + ' · ' + finding['status'])
                    st.text(finding['action'])
        st.caption('Actions are recommendations. This application does not execute them.')
    with trace_tab:
        st.caption('Actual tool calls and policy data. This is an execution record, not hidden model reasoning.')
        st.json(saved['metadata'])
        st.json(saved['trace'])
    st.download_button('Download assessment JSON', json.dumps(saved, indent=2),
                       file_name='assessment.json', mime='application/json', use_container_width=True)
else:
    st.info('Load an example or enter your own fictional scenario, then select Assess scenario. Findings will appear here.')

with st.expander('Reference: all eight governance requirements'):
    for policy in POLICIES:
        st.text(f"{policy['id']}: {policy['requirement']}")
