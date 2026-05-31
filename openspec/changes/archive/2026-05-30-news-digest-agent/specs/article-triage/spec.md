## ADDED Requirements

### Requirement: Select substantively significant stories
The system SHALL use an LLM (Claude Haiku) to evaluate all article titles and descriptions for a category and select 1-3 stories that have genuine real-world impact or significance. The LLM SHALL be instructed to reject: sensationalist headlines, outrage-cycle content, celebrity drama with no broader consequence, and stories whose significance lies only in who said something rather than what was decided or happened.

#### Scenario: Normal day with mixed quality articles
- **WHEN** a category has 10-40 articles with a mix of substantive and sensational content
- **THEN** the system returns 1-3 articles selected for substantive impact, excluding clickbait and noise

#### Scenario: No worthy stories today
- **WHEN** the LLM determines no articles in a category meet the significance threshold
- **THEN** the system returns an empty list for that category and the category is omitted from the digest

#### Scenario: All articles are significant
- **WHEN** the LLM determines more than 3 articles are genuinely significant
- **THEN** the system returns the top 3 by significance and discards the rest

### Requirement: Triage is per-category
The system SHALL run triage independently for each category, using a category-specific context hint in the prompt (e.g., "this is a science news category") to help the LLM apply appropriate judgment for what counts as significant.

#### Scenario: Category context in prompt
- **WHEN** triage runs for the "science" category
- **THEN** the LLM prompt includes a hint that this is science news and significance should be judged accordingly

### Requirement: Triage respects deduplication
The system SHALL exclude articles already seen in previous runs (per the deduplication store) from the candidate list before passing to the LLM for triage.

#### Scenario: Previously seen article appears again
- **WHEN** an article URL is present in the deduplication store
- **THEN** that article is not passed to the LLM for triage consideration
