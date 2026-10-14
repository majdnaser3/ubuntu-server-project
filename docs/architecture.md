# Architecture

## Intended high-level design

Windows Flet client ─┐
Android Flet client ─┼── HTTP API ── Ubuntu Server ── per-user file storage
Web browser ─────────┘

All clients use the same backend. The backend authenticates users, checks authorization, and performs file operations.

## Core principles

- Authentication is handled centrally by the backend.
- The backend—not the client—enforces access permissions.
- Every file operation is scoped to the authenticated user unless an explicitly authorized sharing feature is added.
- User-supplied file paths must never be trusted as filesystem paths.
- Private file storage must not be served directly by an unrestricted static web server.
- Secrets and local configuration stay outside version control.
- Initial operation is local-network-only.

## Proposed components (not yet implemented)

- Python API backend, provisionally FastAPI.
- Persistent account and file metadata store; database selection pending.
- Filesystem storage on the Ubuntu laptop internal drive.
- HTML/CSS/JavaScript web interface.
- Flet Windows client.
- Flet Android client.

This document describes intended architecture, not completed functionality.
