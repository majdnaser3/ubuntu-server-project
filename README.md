# Ubuntu Server Project

A self-hosted personal cloud for storing and managing files over a local network.

The goal is to let multiple users sign in with separate accounts and access their own files from a web browser, a Windows application, and an Android application. All clients will use the same Ubuntu-hosted backend and storage.

## Planned features

- Multiple user accounts and login
- Private per-user files and folders
- Upload, download, browse, rename, and delete files
- Access from web, Windows, and Android
- Local-network operation without public internet exposure
- Documentation that allows other people to reproduce the setup

## Planned architecture

- Server: Ubuntu Server
- Backend/API: Python with FastAPI (to be validated during implementation)
- Web client: HTML, CSS, and JavaScript
- Desktop and Android clients: Flet
- Storage: internal server drive, with per-user isolation
- Version control: Git and GitHub

## Project status

This project is in its initial setup stage. See [PROJECT_STATUS.md](PROJECT_STATUS.md) and [ROADMAP.md](ROADMAP.md).

## Security principles

- Authentication is required for private file access.
- Users must not access other users' private files.
- Secrets, passwords, private keys, and user files must not be committed.
- The initial version is intended for the local network only.
- Public internet access is out of scope for the initial version.

## Reproducibility

Installation instructions, configuration examples, testing steps, and known limitations will be documented as the project develops. Planned features will not be described as completed features.

## License

License not selected yet.
