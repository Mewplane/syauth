# Work on the documentation

The documentation uses MkDocs Material with the same Markdown-first approach as codefang. Content lives under `docs/`; `mkdocs.yml` defines navigation and excludes older flat guides that contain superseded descriptions. Those files remain available in the repository for historical context.

## Preview and check

The locked toolchain is checked with Python 3.12 in CI. From the repository root, create an isolated Python environment and install the pinned documentation dependencies:

```sh
python3 -m venv target/docs-venv
target/docs-venv/bin/python -m pip install -r requirements-docs.txt
target/docs-venv/bin/python -m mkdocs serve --dev-addr 127.0.0.1:8000
```

Open `http://127.0.0.1:8000`. Local fonts, artwork, styles, animation code, and search assets ship with the built site; no external font or animation service is needed. Use a local HTTP server for the built site so browser search workers can run.

Build and run the browser checks:

```sh
target/docs-venv/bin/python -m mkdocs build --strict
target/docs-venv/bin/python -m playwright install chromium
target/docs-venv/bin/python scripts/docs-check.py
```

The generated site lives in `target/docs-site/`, outside the source tree. Linux environments may need Playwright's browser system dependencies; its installer reports missing libraries. CI builds and checks pull requests. On `master`, the workflow copies the shell installer to the site root and deploys the checked output to [GitHub Pages](https://mewplane.github.io/syauth/). Running the preview or checks locally does not publish a site.

## Choose the right page

| Reader's need | Location | Shape |
| --- | --- | --- |
| Learn through a successful example | `docs/tutorials/` | Prerequisites, guided steps, verification, next steps |
| Complete an operational task | `docs/how-to/` | Goal, prerequisites, actions, result |
| Look up a fact | `docs/reference/` | Exact fields, options, defaults, and behavior |
| Understand a mechanism or trade-off | `docs/explanation/` | Why it exists, how it works, boundaries, alternatives |

Link between these page types instead of mixing a tutorial with an exhaustive flag table. Use sentence-case headings, active voice, concrete examples, and links to source for implementation claims. Rust API reference remains in source comments and `cargo doc`.

## Keep mechanics accurate

Read the active caller path, not just helper functions or design comments. The mechanism pages pin their source links to revision `648375e` so the documented observations are reviewable. When behavior changes, update both prose and the corresponding animation in `docs/javascripts/mechanics.js`, then re-run browser checks.

For protocol, pairing, storage, or PAM policy changes, also follow `AGENTS.md` and the specification gate. Documentation must not silently redefine SPEC §3.2 D1–D8. Describe verified discrepancies explicitly; do not convert a design target into an implementation claim.

## Visual and accessibility contracts

Use the Android app's black, white, surface, border, status, and muted-text colors. The pink pads and gold key come from the existing pixel paw artwork in `assets/syauth.png`. Preserve readable text contrast and visible keyboard focus.

The logo preserves the original composition with the key in front of the paw, held by one broad fifth digit attached at the paw's right edge and tipped with a small pixel claw. The four raised toes and their pink pads remain intact. The project owner manually refined the current artwork; `assets/syauth.png` is the authoritative source. Provenance and the preceding generation prompt live in `assets/syauth-logo.prompt.txt`. Keep the root logo, documentation copy, and Android `drawable-nodpi/ic_launcher_foreground.png` identical when updating the artwork.

Animations are opt-in teaching aids. The original SVG scenes use numbered message paths and progressive disclosure, informed by [ByteByteGo's protocol explainers](https://bytebytego.com/guides/how-does-https-work/). The devices, state changes, and storyboards are authored for syauth.

Keep Play/Pause, Previous step, Next step, Restart, chapter selection, and playback speed operable by keyboard. Honor reduced motion, pause when the page is hidden, and retain the complete Markdown transcripts so the explanation works with JavaScript disabled. Mobile scenes reflow into portrait diagrams; do not shrink a desktop diagram until its labels become unreadable. Avoid instructions based solely on color or motion.

The prose follows the [Diátaxis](https://diataxis.fr/) categories and the Good Docs Project tutorial structure; it is original syauth content. The existing mascot remains the project's artwork. Third-party site tooling retains its own package licenses.

<!-- Structure: Diátaxis contributor how-to/reference; original prose for syauth. -->
