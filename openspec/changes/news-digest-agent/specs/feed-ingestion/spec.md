## ADDED Requirements

### Requirement: Fetch RSS feeds per category
The system SHALL fetch all configured RSS/Atom feed URLs for a given category and return normalized article entries. Only articles published within the relevant time window SHALL be returned: 24 hours for daily categories, 7 days for weekly categories.

#### Scenario: Daily category fetch
- **WHEN** a daily category is processed
- **THEN** the system fetches all feeds for that category and returns only articles published in the last 24 hours

#### Scenario: Weekly category fetch
- **WHEN** a weekly category is processed
- **THEN** the system fetches all feeds for that category and returns only articles published in the last 7 days

#### Scenario: Feed fetch failure
- **WHEN** an HTTP request to a feed URL fails or returns a non-200 response
- **THEN** the system logs the error and continues processing remaining feeds for that category without aborting

### Requirement: Normalize feed entries
The system SHALL normalize feed entries from different feed formats (RSS 2.0, Atom) into a consistent internal structure containing: title, URL, published timestamp, and description/summary.

#### Scenario: Missing description
- **WHEN** a feed entry has no description or summary field
- **THEN** the system sets the description to an empty string and continues processing

#### Scenario: Missing published date
- **WHEN** a feed entry has no published timestamp
- **THEN** the system uses the current time as the published timestamp and includes the entry
