# Figma Update Workflow

Use this workflow when the dashboard UI is designed in Figma and then updated in this local LAN console.

## 1. Design rules in Figma

- Build one top-level frame for each dashboard screen: `Overview`, `Naming`, `Devices`, `Storage`, and `Pairing`.
- Keep reusable controls as components: buttons, nav tabs, badges, disk rows, forms, and compact list rows.
- Name layers semantically. Good names are `SyncPercent`, `AddDeviceForm`, `LanguageSelect`, and `DiskRow`.
- Keep text in English where possible if it represents a UI token; the app will localize text through `static/app.js`.
- Prefer variables/tokens for color, spacing, and type instead of ad hoc values.

## 2. Hand off a node-specific Figma URL

Share a URL that includes `node-id`, for example:

```text
https://figma.com/design/FILE_KEY/FileName?node-id=123-456
```

The update process needs the exact frame node. A file-level URL is not enough.

## 3. Update the implementation

The dashboard front end lives here:

```text
static/index.html
static/styles.css
static/app.js
```

Implementation rules:

- Preserve API contracts from `server.py`.
- Keep all visible user-facing strings in the `i18n` dictionary in `static/app.js`.
- Do not hardcode private device IDs or tokens into committed files.
- Keep the first screen operational. This is a control console, not a landing page.
- Validate desktop and mobile layouts after every Figma-driven update.

## 4. Verification checklist

Run:

```sh
python3 -m py_compile server.py project_packager.py generate_windows_config.py
node --check static/app.js
python3 server.py
```

Then check:

- `http://127.0.0.1:8765/api/overview`
- `http://127.0.0.1:8765/api/pairing`
- Language switch between Chinese and English.
- Mobile width around 390px.
- Pairing form, storage form, and project registration form do not overflow.

## 5. Optional Figma-to-code path

When using Codex with the Figma connector:

1. Read the frame with `get_design_context`.
2. Compare the generated design context against the existing dashboard structure.
3. Update `index.html`, `styles.css`, and `app.js` manually, preserving API behavior.
4. Run the verification checklist before deploying the Mac service.
