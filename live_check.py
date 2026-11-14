"""Live model regression checks. Uses two API calls per case; consumes quota."""
import argparse
import json
import os
from pathlib import Path

from agent import assess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all', action='store_true', help='Test both examples and explicit violations (six API calls total).')
    parser.add_argument('--case', choices=['customer', 'security'], default='customer',
                        help='Choose one baseline example (two API calls).')
    args = parser.parse_args()
    samples = json.loads(Path(__file__).with_name('scenarios.json').read_text())
    cases = [('Original customer support scenario', samples['Customer Support Assistant'],
              {'AI-001': 'Insufficient information', 'AI-002': 'Insufficient information',
               'AI-003': 'Met', 'AI-004': 'Insufficient information',
               'AI-005': 'Insufficient information', 'AI-006': 'Insufficient information',
               'AI-007': 'Insufficient information', 'AI-008': 'Insufficient information'}, False)]
    security_case = ('Original internal security scenario', samples['Internal Security Assistant'],
                     {p: ('Met' if p == 'AI-003' else 'Insufficient information')
                      for p in ['AI-001', 'AI-002', 'AI-003', 'AI-004', 'AI-005', 'AI-006', 'AI-007', 'AI-008']},
                     False)
    if args.all:
        cases.append(security_case)
    elif args.case == 'security':
        cases = [security_case]
    if args.all:
        cases.append(('Explicit violations',
                      'We will deploy a customer support AI using a third-party hosted LLM API. '
                      'Customer account information will be sent without any protective controls. '
                      'We will deploy the third-party service without a security assessment.',
                      {'AI-002': 'Gap identified', 'AI-006': 'Gap identified'}, True))
    failures = []
    for name, scenario, expected, expected_review in cases:
        print('\n' + name, flush=True)
        result, trace = assess(scenario, os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b'), progress=print)
        actual = {f['policy_id']: f['status'] for f in result['findings']}
        for policy_id, status in expected.items():
            passed = actual[policy_id] == status
            print(f"{'PASS' if passed else 'FAIL'} {policy_id}: {actual[policy_id]} (expected {status})")
            if not passed:
                failures.append(name + ': ' + policy_id)
        if result['review_recommended'] != expected_review:
            failures.append(name + ': review flag')
            print('FAIL: additional-review flag differs from the prototype screening expectation.')
        print('Inspect summary, quotations, explanations, and actions manually as well.')
    if failures:
        raise SystemExit('Regression check failed: ' + ', '.join(failures))
    print('\nLive regression checks passed. This does not establish general model reliability.')


if __name__ == '__main__':
    main()
