# Roadmap

This roadmap is a living plan. Update it when scope, architecture, or progress changes.

## Phase 0 — Project foundation
- [x] Create the local project folder.
- [x] Preserve local planning PDFs and exclude them from Git.
- [ ] Create initial documentation.
- [ ] Initialize Git and review the first commit.
- [ ] Create and connect the public GitHub repository.

## Phase 1 — Audit the existing Ubuntu server
- [ ] Verify Ubuntu version, hostname, hardware, disk, and network configuration.
- [ ] Verify local IP and connectivity from Windows.
- [ ] Verify SSH access.
- [ ] Record existing services and installations.
- [ ] Document any changes already made; avoid unnecessary reinstallations.

## Phase 2 — Define architecture and security
- [ ] Confirm the backend/API and configuration approach.
- [ ] Define user accounts, roles, sessions, and password handling.
- [ ] Define private per-user storage and permissions.
- [ ] Define upload limits, safe paths, and error handling.
- [ ] Document the local-network-only threat model.

## Phase 3 — Server foundation
- [ ] Prepare a dedicated application/service account.
- [ ] Prepare storage directories and permissions.
- [ ] Set up the backend environment and dependency management.
- [ ] Add configuration examples without secrets.
- [ ] Add automated tests.

## Phase 4 — Backend and accounts
- [ ] Implement account creation and login.
- [ ] Store password hashes, never plaintext passwords.
- [ ] Implement authenticated file listing and folder operations.
- [ ] Implement upload and download.
- [ ] Enforce per-user authorization on every relevant operation.
- [ ] Test invalid paths and cross-account access.

## Phase 5 — Web client
- [ ] Build login and logout.
- [ ] Build file and folder browsing.
- [ ] Build upload and download flows.
- [ ] Test with multiple accounts.

## Phase 6 — Windows Flet client
- [ ] Establish stable package and application identifiers.
- [ ] Build server connection settings and login.
- [ ] Implement file management.
- [ ] Build and test a Windows release.

## Phase 7 — Android Flet client
- [ ] Establish stable application ID/package name before building.
- [ ] Implement connection settings and login.
- [ ] Implement file management and Android permissions.
- [ ] Build, install, and test the APK on a real device.

## Phase 8 — Reliability and security
- [ ] Test server restart and data persistence.
- [ ] Test simultaneous use from multiple devices.
- [ ] Test account isolation and session handling.
- [ ] Document backup and test restoration.
- [ ] Document firewall and network configuration.

## Phase 9 — Reproducible setup
- [ ] Write step-by-step Ubuntu installation and configuration instructions.
- [ ] Test the instructions on a clean environment or separate installation.
- [ ] Add troubleshooting guidance.
- [ ] Consider a setup wizard only after the manual process is proven.

## Phase 10 — Public release
- [ ] Review repository for secrets and private data.
- [ ] Complete a clean-install test using the documentation.
- [ ] Publish tested Windows and Android builds.
- [ ] Document known limitations and release version.
- [ ] Create a GitHub release.

## Deferred until after the initial version
- Public remote access.
- Automatic file synchronization or photo uploads.
- External-drive support.
- Advanced shared folders and administration.
- Automatic device discovery.
