# Contributing

## Local checks

Run these before submitting changes:

```sh
python3 -m py_compile server.py project_packager.py generate_windows_config.py
node --check static/app.js
```

If you changed the UI, also test:

- Chinese and English language switching.
- Desktop width around 1280px.
- Mobile width around 390px.
- Pairing, storage, and naming workflows.

## Code style

- Keep the Python server dependency-free unless a feature clearly needs more.
- Keep all user-facing web text in the `i18n` dictionary in `static/app.js`.
- Keep file operations conservative. The normalization workflow must not mutate the source project.
- Do not commit private device IDs, IP addresses, MAC addresses, API keys, or tokens.

## Pull requests

Describe:

- What changed.
- What was tested.
- Any Syncthing version assumptions.
- Any OS-specific behavior.
