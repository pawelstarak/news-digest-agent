## Requirements

### Requirement: Track processed article URLs
The system SHALL maintain a deduplication store of article URLs that have been included in previous digests. The store SHALL use a rolling 48-hour window: entries older than 48 hours SHALL be removed at the end of each run.

#### Scenario: Article seen in previous run
- **WHEN** an article URL is present in the deduplication store
- **THEN** that article is excluded from triage candidates for the current run

#### Scenario: New article not in store
- **WHEN** an article URL is not present in the deduplication store
- **THEN** that article is eligible for triage

### Requirement: Persist state in Azure Blob Storage
The deduplication store SHALL be persisted as a JSON blob in Azure Blob Storage. The system SHALL load the store at the start of each run and write it back at the end of the run after adding newly processed URLs and trimming expired entries.

#### Scenario: First run (empty store)
- **WHEN** no deduplication blob exists in storage yet
- **THEN** the system initializes an empty store and proceeds normally

#### Scenario: Storage read failure
- **WHEN** the Azure Blob Storage read fails at the start of a run
- **THEN** the system logs the error and proceeds with an empty in-memory store (no deduplication for this run), but does NOT abort the run

#### Scenario: Storage write failure
- **WHEN** the Azure Blob Storage write fails at the end of a run
- **THEN** the system logs the error. The digest email is still sent. Deduplication state for this run is lost but the run is not considered failed.

### Requirement: Store only selected article URLs
The system SHALL only add to the deduplication store URLs of articles that were actually selected by triage and included in the digest. Articles that were fetched but not selected SHALL NOT be stored.

#### Scenario: Article fetched but not selected
- **WHEN** an article is fetched from an RSS feed but the LLM triage does not select it
- **THEN** its URL is not added to the deduplication store
