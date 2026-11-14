"""Offline tests: validate guardrails and exercise the complete loop with a fake API."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from agent import POLICIES, assess, attach_evidence, source_sentences, call_model, validate_assessment
import requests


def sample_result():
    return {'summary': 'More information is needed.', 'review_recommended': True,
            'review_reason': 'Risk screening needs clarification.', 'findings': [
                {'policy_id': p['id'], 'status': 'Insufficient information', 'evidence': '', 'evidence_source_ids': [],
                 'explanation': 'No supporting details.', 'action': 'Request supporting documentation.'}
                for p in POLICIES]}


class AgentTests(unittest.TestCase):
    def test_all_policies_required(self):
        result = sample_result()
        result['findings'][0]['policy_id'] = 'AI-002'
        with self.assertRaises(ValueError):
            validate_assessment(result, 'Example')

    def test_fabricated_quote_rejected(self):
        result = sample_result()
        result['findings'][0]['evidence'] = 'Invented owner'
        with self.assertRaises(ValueError):
            validate_assessment(result, 'Example')

    def test_met_requires_quote(self):
        result = sample_result()
        result['findings'][0]['status'] = 'Met'
        with self.assertRaises(ValueError):
            validate_assessment(result, 'Example')

    @patch.dict(os.environ, {'GROQ_API_KEY': 'fake-test-key'})
    def test_agent_loop(self):
        tool_message = {'role': 'assistant', 'content': None, 'tool_calls': [
            {'id': 'call_1', 'type': 'function', 'function': {
                'name': 'get_requirements', 'arguments': '{}'}}]}
        with patch('agent.call_model', side_effect=[tool_message, {'content': json.dumps(sample_result())}]) as api:
            updates = []
            result, trace = assess('Fictional example', 'test-model', progress=updates.append)
        self.assertEqual(len(result['findings']), 8)
        self.assertEqual(trace[0]['tool'], 'get_requirements')
        self.assertEqual(api.call_count, 2)
        final_messages = api.call_args_list[1].args[0]
        self.assertEqual([m['role'] for m in final_messages], ['system', 'user'])
        self.assertNotIn('Retrieve requirements with get_requirements before answering',
                         final_messages[0]['content'])
        self.assertIn('ALREADY run', final_messages[0]['content'])
        self.assertIn('Missing evidence is NOT evidence of a violation', final_messages[0]['content'])
        self.assertIn('Missing governance details alone do not trigger', final_messages[0]['content'])
        self.assertIn('AI-008', final_messages[0]['content'])
        self.assertIn('automatically deciding promotions', final_messages[0]['content'])
        self.assertIn('review_recommended=true', final_messages[0]['content'])
        self.assertIn('documented intended use and', final_messages[0]['content'])
        self.assertIn('NEVER mark AI-006 Not applicable using internal/cloud hosting',
                      final_messages[0]['content'])
        self.assertEqual(json.loads(final_messages[1]['content'])['scenario'], 'Fictional example')
        self.assertEqual(len(updates), 4)

    @patch.dict(os.environ, {'GROQ_API_KEY': 'fake-test-key'})
    def test_unapproved_tool_blocked(self):
        message = {'role': 'assistant', 'tool_calls': [{'id': 'bad', 'function': {
            'name': 'run_shell', 'arguments': '{}'}}]}
        with patch('agent.call_model', return_value=message):
            with self.assertRaises(ValueError):
                assess('Fictional example', 'test-model')

    def test_timeout_has_safe_message(self):
        with patch('agent.requests.post', side_effect=requests.Timeout):
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                call_model([], 'test-model', 'fake-key', True)

    def test_request_limits(self):
        with patch('agent.requests.post') as post:
            post.return_value.ok = True
            post.return_value.status_code = 200
            post.return_value.json.return_value = {'choices': [{'message': {}}]}
            call_model([], 'openai/gpt-oss-20b', 'fake-key', True)
            self.assertEqual(post.call_args.args[0], 'https://api.groq.com/openai/v1/chat/completions')
            self.assertEqual(post.call_args.kwargs['timeout'], (10, 60))
            self.assertEqual(post.call_args.kwargs['json']['reasoning_effort'], 'low')
            self.assertEqual(post.call_args.kwargs['json']['max_tokens'], 1024)
            self.assertEqual(post.call_args.kwargs['json']['tool_choice'], 'required')

    def test_assessment_request_settings(self):
        with patch('agent.requests.post') as post:
            post.return_value.ok = True
            post.return_value.status_code = 200
            post.return_value.json.return_value = {'choices': [{'message': {}}]}
            call_model([], 'test-model', 'fake-key', False)
            self.assertEqual(post.call_args.kwargs['timeout'], (10, 120))
            self.assertEqual(post.call_args.kwargs['json']['max_tokens'], 4000)
            self.assertNotIn('tools', post.call_args.kwargs['json'])

    def test_truncated_assessment_rejected(self):
        with patch('agent.requests.post') as post:
            post.return_value.ok = True
            post.return_value.status_code = 200
            post.return_value.json.return_value = {'choices': [
                {'finish_reason': 'length', 'message': {'content': '{'}}]}
            with self.assertRaisesRegex(RuntimeError, 'output limit'):
                call_model([], 'test-model', 'fake-key', False)

    @patch.dict(os.environ, {'GROQ_API_KEY': 'fake-test-key'})
    def test_results_dashboard(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).with_name('app.py'))).run()
        app.selectbox[0].select('Customer Support Assistant').run()
        app.checkbox[0].check().run()
        with patch('agent.assess', return_value=(sample_result(), [])), \
             patch('audit.record_event', return_value={'assessment_id': 'test'}):
            next(b for b in app.button if b.label == 'Assess scenario').click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.metric), 4)
        self.assertEqual(len(app.tabs), 3)
        app.multiselect[0].set_value(['Met']).run()
        self.assertTrue(any('No findings match' in i.value for i in app.info))
        app.text_area[0].set_value('Changed scenario').run()
        self.assertEqual(len(app.metric), 0)

    def test_provider_error_is_redacted(self):
        with patch('agent.requests.post') as post:
            post.return_value.ok = False
            post.return_value.status_code = 400
            post.return_value.json.return_value = {'error': {
                'message': 'Unsupported parameter fake-secret', 'failed_generation': 'private payload'}}
            with self.assertRaises(RuntimeError) as error:
                call_model([], 'test-model', 'fake-secret', True)
            self.assertIn('Unsupported parameter', str(error.exception))
            self.assertNotIn('fake-secret', str(error.exception))
            self.assertNotIn('private payload', str(error.exception))

    def test_evidence_is_copied_from_original(self):
        scenario = 'Owner is Sara.  Logging is enabled.\nMonitoring is enabled.'
        result = sample_result()
        result['findings'][0].update(evidence_source_ids=[1], evidence='Invented quotation', status='Met')
        result = attach_evidence(result, scenario, source_sentences(scenario))
        self.assertEqual(result['findings'][0]['evidence'], 'Owner is Sara.')
        validate_assessment(result, scenario)

    def test_unknown_source_is_rejected(self):
        result = sample_result()
        result['findings'][0]['evidence_source_ids'] = [999]
        with self.assertRaises(ValueError):
            attach_evidence(result, 'Example.', source_sentences('Example.'))

    def test_multiple_sources_preserve_original_spacing(self):
        scenario = 'Logging is enabled.  Monitoring is enabled.'
        result = sample_result()
        result['findings'][0]['evidence_source_ids'] = [1, 2]
        result = attach_evidence(result, scenario, source_sentences(scenario))
        self.assertEqual(result['findings'][0]['evidence'], scenario)

    def test_screen(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).with_name('app.py'))).run()
        self.assertEqual(len(app.exception), 0)
        next(b for b in app.button if b.label == 'Assess scenario').click().run()
        self.assertEqual(app.error[0].value, 'Enter a scenario first.')
        for name, phrase in [('Customer Support Assistant', 'customer names'),
                             ('Internal Security Assistant', 'security alerts'),
                             ('Automated Employee Decisions', 'promotion')]:
            app.selectbox[0].select(name).run()
            self.assertIn(phrase, app.text_area[0].value)
        next(b for b in app.button if b.label == 'Assess scenario').click().run()
        self.assertIn('Confirm fictional data', app.error[0].value)


if __name__ == '__main__':
    unittest.main()
