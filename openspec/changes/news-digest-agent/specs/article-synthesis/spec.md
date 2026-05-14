## ADDED Requirements

### Requirement: Fetch full article text
For each triaged article, the system SHALL attempt to fetch the full article text from the article URL. If the fetch succeeds, the full text SHALL be used as the basis for synthesis. If the fetch fails (network error, paywall, non-HTML response), the system SHALL fall back to the RSS description/summary.

#### Scenario: Successful full-text fetch
- **WHEN** an HTTP GET to the article URL returns parseable HTML content
- **THEN** the system extracts the main article body text and uses it for synthesis

#### Scenario: Full-text fetch fails
- **WHEN** an HTTP GET to the article URL fails, times out, or returns a paywall/login page
- **THEN** the system logs the failure and uses the RSS description/summary as fallback content for synthesis

### Requirement: Synthesize with context
The system SHALL use Claude Sonnet to produce a synthesis of each selected article. The synthesis SHALL include: a concise factual summary of what happened, relevant background context (why this matters, what led to this), and a brief interpretive framing (what might happen next, what the implications are). The synthesis SHALL NOT repeat the headline verbatim, SHALL NOT use clickbait language, and SHALL NOT include the journalist's own speculation unless clearly attributed.

#### Scenario: Standard synthesis
- **WHEN** article text is available for synthesis
- **THEN** the output includes a summary paragraph, a context paragraph, and an implications sentence, written in plain informative prose

#### Scenario: Synthesis from RSS fallback
- **WHEN** only the RSS description is available (full text fetch failed)
- **THEN** the system still produces a synthesis, clearly noting that the summary is based on limited source text

### Requirement: Prompt caching on synthesis system prompt
The system SHALL structure synthesis LLM calls so that the system prompt (persona, instructions, output format) is eligible for Anthropic prompt caching. The system prompt SHALL be identical across all synthesis calls in a single run.

#### Scenario: Multiple stories in a run
- **WHEN** the digest run synthesizes 5 or more stories
- **THEN** the system prompt is cached after the first call and subsequent calls benefit from the cache hit
