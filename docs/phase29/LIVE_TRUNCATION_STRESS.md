# Live truncation stress

Eighteen OpenAI calls compared plain JSON, native structured output and compact schema at 25, 50,
75, 100, 125 and 150 percent of a preregistered 160-word visible-output calibration with a fixed
256-token provider limit. All 9 calls through 75% committed. All 9 calls at 100–150% terminated as
`TRUNCATED_OUTPUT`; provider finish reason was `max_output_tokens` and classification preceded JSON
parsing in every case. There were no generic parse or schema misclassifications. Total cost was
$0.0182295. Evidence: `evidence/truncation_live_v1/report.json`.
