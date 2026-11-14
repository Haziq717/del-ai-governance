"""Offline tests: validate guardrails and exercise the complete loop with a fake API."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from agent import POLICIES, assess, validate_assessment


def sample_result():
    return {'summary': 'More information is needed.', 'review_recommended': True,
            'review_reason': 'Risk screening needs clarification.', 'findings': [
                {'policy_id': p['id'], 'status': 'Insufficient information', 'evidence': '',
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

    @patch.dict(os.environ, {'GEMINI_API_KEY': 'fake-test-key'})
    def test_agent_loop(self):
        tool_message = {'role': 'assistant', 'content': None, 'tool_calls': [
            {'id': 'call_1', 'type': 'function', 'function': {
                'name': 'get_requirements', 'arguments': '{}'}}]}
        with patch('agent.call_model', side_effect=[tool_message, {'content': 'Ready'},
                                                    {'content': json.dumps(sample_result())}]) as api:
            result, trace = assess('Fictional example', 'test-model')
        self.assertEqual(len(result['findings']), 8)
        self.assertEqual(trace[0]['tool'], 'get_requirements')
        self.assertEqual(api.call_count, 3)

    @patch.dict(os.environ, {'GEMINI_API_KEY': 'fake-test-key'})
    def test_unapproved_tool_blocked(self):
        message = {'role': 'assistant', 'tool_calls': [{'id': 'bad', 'function': {
            'name': 'run_shell', 'arguments': '{}'}}]}
        with patch('agent.call_model', return_value=message):
            with self.assertRaises(ValueError):
                assess('Fictional example', 'test-model')

    def test_screen(self):
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).with_name('app.py'))).run()
        self.assertEqual(len(app.exception), 0)
        app.button[0].click().run()
        self.assertEqual(app.error[0].value, 'Enter a scenario first.')
        for name, phrase in [('Customer Support Assistant', 'customer names'),
                             ('Internal Security Assistant', 'security alerts'),
                             ('Automated Employee Decisions', 'promotion')]:
            app.selectbox[0].select(name).run()
            self.assertIn(phrase, app.text_area[0].value)
        app.button[0].click().run()
        self.assertIn('Confirm fictional data', app.error[0].value)


if __name__ == '__main__':
    unittest.main()
