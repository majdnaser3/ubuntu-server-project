# Architecture and Project Decisions

This file records decisions and their status. Proposed choices are not final until validated.

## Confirmed requirements

### Multiple accounts
Status: Confirmed.
Each person has their own login. One account can be used on multiple devices.

### Private files by default
Status: Confirmed.
A user cannot access another user's files unless an explicit sharing feature is later implemented.

### Local-network-only initial version
Status: Confirmed.
No router port forwarding or public service exposure is planned for the initial version.

### Shared backend
Status: Confirmed.
The web, Windows, and Android clients use the same API and storage.

### Flet for desktop and Android
Status: Confirmed.
The Windows and Android applications will use Flet. Application identifiers and packaging configuration must be documented and tested early.

### Documentation before setup wizard
Status: Confirmed.
The manual setup guide must be written and tested before building a setup wizard.

## Proposed technical choices

### FastAPI backend
Status: Proposed; validate before implementation.

### Metadata database
Status: Pending.
Choose a database after defining account, session, and file metadata requirements.

### User storage layout
Status: Pending.
Select a layout that enforces per-user isolation and supports safe file operations.

### License
Status: Pending.
Select an appropriate open-source license before public release.

## Security rule
The clients must not receive unrestricted SSH or administrator-shell access. Server setup automation, if added, must use controlled, explicitly authorized actions.
