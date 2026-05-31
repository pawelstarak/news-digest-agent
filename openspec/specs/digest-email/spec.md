## Requirements

### Requirement: Compose HTML digest email
The system SHALL compose a formatted HTML email containing all synthesized stories grouped by category. Categories with no selected stories SHALL be omitted. Daily categories SHALL appear before weekly categories. Each story SHALL include: the original article title as a hyperlink, the synthesis text, and the source feed name.

#### Scenario: Normal digest with multiple categories
- **WHEN** the run produces stories in 3 or more categories
- **THEN** the email body contains one clearly delineated section per category, with stories listed within each section

#### Scenario: No stories for any category
- **WHEN** triage returns no stories across all categories for the day
- **THEN** no email is sent and the absence is logged

#### Scenario: Weekly categories on a daily run
- **WHEN** the run day does not match the configured day for a weekly category
- **THEN** that category is entirely absent from the email

### Requirement: Send via Gmail SMTP
The system SHALL send the composed digest email using Gmail SMTP with credentials (username and App Password) provided via environment variables. The recipient email SHALL also be provided via environment variable.

#### Scenario: Successful send
- **WHEN** the digest email is composed and SMTP credentials are configured
- **THEN** the email is sent to the configured recipient and the successful send is logged

#### Scenario: SMTP failure
- **WHEN** the Gmail SMTP connection or authentication fails
- **THEN** the system logs the error with full details. The digest content (HTML) SHALL also be written to a local log file so no digest is silently lost.

### Requirement: Email subject includes date
The email subject SHALL include the current date so the recipient can easily identify digests in their inbox.

#### Scenario: Subject format
- **WHEN** an email is sent on 2026-05-14
- **THEN** the subject is "News Digest — 14 May 2026" (or equivalent locale-appropriate format)
