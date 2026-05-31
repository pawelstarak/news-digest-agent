## Requirements

### Requirement: YAML configuration file
The system SHALL read all category and feed configuration from a YAML file (`config.yaml`) at the project root. The configuration SHALL define: a list of categories, each with a name, frequency (daily or weekly), optional weekday for weekly categories, and a list of feed sources (each with a URL and a display name).

#### Scenario: Valid config loaded
- **WHEN** the config file exists and is valid YAML with at least one category
- **THEN** the system uses the configured categories and feeds for the run

#### Scenario: Config file missing
- **WHEN** the config file does not exist at the expected path
- **THEN** the system raises a clear error and aborts the run

#### Scenario: Config file has invalid YAML
- **WHEN** the config file contains a YAML syntax error
- **THEN** the system raises a clear error identifying the file and aborts the run

### Requirement: Category frequency configuration
Each category SHALL specify a `frequency` field with value `daily` or `weekly`. Weekly categories SHALL include a `day` field specifying the day of week as a lowercase string (e.g., `friday`). If `day` is omitted for a weekly category, the system SHALL default to `friday`.

#### Scenario: Daily category runs every day
- **WHEN** a category has `frequency: daily`
- **THEN** it is processed on every run regardless of day of week

#### Scenario: Weekly category runs on configured day
- **WHEN** a category has `frequency: weekly` and `day: friday`
- **THEN** it is processed only when the current day of week is Friday

#### Scenario: Weekly category with no day specified
- **WHEN** a category has `frequency: weekly` but no `day` field
- **THEN** the system treats it as `day: friday`

### Requirement: Delivery configuration
The config file SHALL include a `delivery` section with: `time` (the target local time for the digest, informational only — actual scheduling is handled by Azure Functions), and `timezone` (IANA timezone string used to determine the current day of week for weekly category selection).

#### Scenario: Timezone used for day-of-week determination
- **WHEN** the Azure Function runs at 06:00 UTC and timezone is `Europe/Warsaw`
- **THEN** the system uses the Europe/Warsaw local date to determine which weekly categories to include
