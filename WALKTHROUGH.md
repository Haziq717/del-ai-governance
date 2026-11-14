# Code walkthrough

Start with `policies.json`: this is the source of the eight requirements. `scenarios.json` contains examples, not training records.

## app.py

Streamlit reruns the file when a widget changes. We load the examples, show a selector and text box, then wait for the assessment button. The checkbox is required before sending fictional text to Google. `st.session_state` retains a completed report across reruns. It is hidden if the input changes, preventing a report for old text from appearing under new text.

The button calls `assess(scenario, model)`. It receives two values: the assessment and the tool trace. It logs metadata and displays each finding. `st.text` displays generated narratives as plain text. The JSON download is a report, not a database entry.

## agent.py

`get_requirements()` returns exact policy text. `get_review_criteria()` returns disclosed prototype screening assumptions. The `TOOLS` dictionary maps approved names to Python functions. The model cannot create executable functions.

`TOOL_SCHEMAS` describes those functions to Gemini. Both take zero arguments, which makes argument validation simple.

`PROMPT` defines the assessment task, evidence rules, and JSON shape. This is a prompt, not a guarantee. The validator is an additional boundary.

`call_model()` makes one HTTP POST. The JSON body includes the model, conversation messages, and either tools or JSON output mode. The Authorization header uses the environment key. HTTP errors become short controlled messages.

`assess()` maintains the conversation in a list called `messages`. When Gemini requests a function, Python checks its name and arguments, executes the approved function, and appends the tool result. After one tool-selection round and local tool execution, it requests the final JSON. Successful assessments use exactly two API calls. An optional progress callback updates the screen without coupling the agent to Streamlit. A policy retrieval is mandatory. This is a bounded agent loop, not multiple agents or a complex framework.

`validate_assessment()` checks eight unique policy IDs, allowed statuses, required text fields, the review flag, and exact quote matches. It cannot independently verify that a quote supports a conclusion. A reviewer must do that.

## audit.py

`record_event()` creates a unique ID and UTC timestamp, then inserts metadata using SQLite placeholders. It does not store raw prompts or API keys. Logging failures are shown to the user rather than silently claiming success.

## test_agent.py

The fake model response tests our orchestration without spending API quota. It does not demonstrate real model quality. Streamlit's testing API checks the input screen and error messages. Real A/B/C assessments still require your key and review.
