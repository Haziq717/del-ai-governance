# Engineering decisions and live-test findings

## Evidence classification: observed problem

In a live assessment of the original customer support example, the model returned one Met, two Gap identified, and five Insufficient information findings. AI-002 and AI-006 were incorrectly marked as gaps. The quoted text established sensitive-data processing and third-party use, but did not establish absent controls or an absent security assessment.

This is a semantic error: exact quotation matching alone could not catch it. The quotations were present, but did not justify the conclusions. The summary also mixed unknown controls with confirmed failures. The review recommendation relied on missing details rather than an established screening indicator.

## Change made

The assessment prompt now includes explicit contrasting examples: unspecified controls versus explicitly unprotected data, and unspecified assessment history versus an explicit plan to deploy without assessment. It requires a final check that every gap quotation contradicts the policy rather than merely establishes relevance. The summary must distinguish unknown facts from confirmed violations. Missing details alone do not establish a high-risk indicator under this prototype's disclosed screening criteria.

No hardcoded scenario result or automatic gap-to-unknown conversion was added. Explicit violations must still be reported as gaps. Existing Python evidence and structure validation remains in place.

## Expected behavior and verification status

For the original customer support scenario, the expected result is one Met (AI-003) and seven Insufficient information findings. AI-002 and AI-006 need clarification. Under the prototype screening criteria, unspecified controls alone do not justify additional risk review; risk classification remains open and this is not deployment approval.

These are expected results, not a claim that the revised live output has passed. Run `python live_check.py` to check the original example (two API calls). Run `python live_check.py --all` to also verify that explicitly unprotected data and an explicitly unassessed third-party deployment remain gaps (four API calls total). Account quota applies. Review the narrative manually too. A passing example does not guarantee all future classifications.

## Presentation wording

“Live testing exposed a distinction between missing evidence and confirmed noncompliance. Our quote validator verified the text existed, but could not verify that it supported the conclusion. I added specific classification examples and a live regression check, while preserving genuine gap detection. I keep human review because semantic correctness is not guaranteed by JSON or quote validation.”

Only say the revised live checks passed after observing their output. Show the actual before/after assessment and the execution trace. Do not fabricate screenshots.

## Interface change

The original dashboard used a dark background. The revised version uses Streamlit's light theme, pale blue-gray page and sidebar backgrounds, white cards, dark navy text, and blue primary actions. Scenario cards, status filters, action lists, and tool traces remain available. Restart the app to load the theme configuration; a browser theme override may need to be reset to the app's light theme.
