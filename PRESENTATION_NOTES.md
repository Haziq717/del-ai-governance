# Engineering decisions and live-test findings

## Evidence classification: observed problem

In a live assessment of the original customer support example, the model returned one Met, two Gap identified, and five Insufficient information findings. AI-002 and AI-006 were incorrectly marked as gaps. The quoted text established sensitive-data processing and third-party use, but did not establish absent controls or an absent security assessment.

This is a semantic error: exact quotation matching alone could not catch it. The quotations were present, but did not justify the conclusions. The summary also mixed unknown controls with confirmed failures. The review recommendation relied on missing details rather than an established screening indicator.

## Change made

The assessment prompt now includes explicit contrasting examples: unspecified controls versus explicitly unprotected data, and unspecified assessment history versus an explicit plan to deploy without assessment. It requires a final check that every gap quotation contradicts the policy rather than merely establishes relevance. The summary must distinguish unknown facts from confirmed violations. Missing details alone do not establish a high-risk indicator under this prototype's disclosed screening criteria.

No hardcoded scenario result or automatic gap-to-unknown conversion was added. Explicit violations must still be reported as gaps. Existing Python evidence and structure validation remains in place.

## Expected behavior and verification status

For the original customer support scenario, the expected result is one Met (AI-003) and seven Insufficient information findings. AI-002 and AI-006 need clarification. Under the prototype screening criteria, unspecified controls alone do not justify additional risk review; risk classification remains open and this is not deployment approval.

These are expected results, not a claim that the revised live output has passed. Run `python live_check.py` to check the original example (two API calls). Run `python live_check.py --all` to also verify that explicitly unprotected data and an explicitly unassessed third-party deployment remain gaps, along with the internal-security example (six API calls total). Account quota applies. Review the narrative manually too. A passing example does not guarantee all future classifications.

## Presentation wording

“Live testing exposed a distinction between missing evidence and confirmed noncompliance. Our quote validator verified the text existed, but could not verify that it supported the conclusion. I added specific classification examples and a live regression check, while preserving genuine gap detection. I keep human review because semantic correctness is not guaranteed by JSON or quote validation.”

Only say the revised live checks passed after observing their output. Show the actual before/after assessment and the execution trace. Do not fabricate screenshots.

## Interface change

The original dashboard used a dark background. The revised version uses Streamlit's light theme, pale blue-gray page and sidebar backgrounds, white cards, dark navy text, and blue primary actions. Scenario cards, status filters, action lists, and tool traces remain available. Restart the app to load the theme configuration; a browser theme override may need to be reset to the app's light theme.

## Evidence quotation repair

A later live run was blocked because a generated quotation did not exactly occur in the scenario. Instead of weakening the quote validator or accepting approximate matches, Python now numbers source text spans before the final request. The model returns `evidence_source_ids`, and Python copies the original text using stored offsets. Invalid source IDs are rejected. When multiple sentences are selected, the displayed quote is the original contiguous span containing them, including intervening text. Empty source IDs mean missing evidence. The original exact-match validator remains as a final check.

This removes the need for the model to reproduce punctuation and spacing. It does not establish that the selected sentence supports the conclusion; that remains subject to human review and live regression testing. This change was verified with offline tests for original-text copying, invalid IDs, and multi-sentence spacing. Revised live results must still be observed before claiming they pass.


## Internal hosting and risk classification: second live finding

In the original internal-security example, a live assessment incorrectly inferred that no third-party model/service was used because deployment was internal. It also claimed that a high-risk classification had been identified, although none was stated. Internal cloud hosting does not establish model provenance: a self-hosted model may still be third-party. Logs may contain sensitive information, but the example does not establish their contents.

The prompt now explicitly separates hosting from model/service provenance, gives a counterexample for self-hosted third-party models, and requires clarification when provenance is unknown. It prohibits inventing high-risk labels from security context alone and asks for risk classification and review evidence. The changes apply generally; no scenario-specific classifications are hardcoded into the assessment engine.

Run `python live_check.py --case security` (two API calls) to check the supplied internal-security example. Expected: AI-003 Met; the other seven policies Insufficient information. Under the disclosed screening criteria, the review flag is false pending clarification, not deployment approval. Manually inspect AI-002 wording and AI-008's explanation as well as counts. `python live_check.py --all` now runs three cases (six API calls). These expected outputs are not claimed as live-verified after the change. Offline checks verify prompt delivery and existing validation/UI behavior, not semantic accuracy.
