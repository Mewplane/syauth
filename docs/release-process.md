# Release process

The maintained release handbook is [Build and publish a release](contributing/releases.md), published on [GitHub Pages](https://mewplane.github.io/syauth/contributing/releases/).

It describes the Debian 12 Linux build baseline, DEB/RPM/Arch packaging, the container installation matrix, persistent Android signing, checksum and source metadata, and tag-triggered publication. The canonical pipeline is `.github/workflows/release.yml`; older mock/pbuilder Makefile targets are not used for release publication.

For installing published artifacts, follow [the installation guide](how-to/install.md). Downloads are attached to [GitHub Releases](https://github.com/Mewplane/syauth/releases/latest).
