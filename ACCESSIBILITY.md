# Accessibility

This repository ships two user-facing surfaces: the Markdown docs on GitHub and the local Ambilight web studio served by `tools/ambilight_controller.py web`. The Python and shell tools print to a terminal.

## Docs and CLI

The docs use headings, link text, tables, and code blocks. GitHub renders them. The CLI tools assume a terminal and do not provide a screen-reader mode. If a table or a command block is hard to use with your setup, open an issue with the page and the assistive technology.

## Ambilight web studio

The studio is a local page with LED selection, color controls, input keys, volume, and macros. It is a convenience UI. The CLI remains the primary control path.

### What works

- The page declares `lang="en"`.
- It uses native checkboxes, a color input, a text input, and range sliders.
- Most actions have text labels.
- Most controls use the browser focus ring.

### Known gaps

- Nobody has audited the page against WCAG 2.2.
- Chips, swatches, and theme tiles are `div` elements with `onclick`. They do not receive keyboard focus and do not expose a button role.
- Icon-only buttons and swatches rely on `title`. Some screen readers do not announce `title` as the accessible name. They need `aria-label` or visible text.
- Screen readers announce emoji in labels. Replace the emoji with text where it obscures the action.
- The LED swatches use color alone. Add a text or shape cue.
- Several labels use 11 to 13 px text. It is hard to read at default zoom.
- The page does not honor `prefers-reduced-motion`.
- The status toast has no `aria-live` region, so screen readers may miss it.
- The hex input removes the focus outline and relies on a border color change.
- Nobody has measured the contrast of the muted text.

## Reporting

Open an issue with the page or control, your browser, your assistive technology, and the steps to reproduce. Remove device identifiers and credentials. If the problem exposes a security boundary in the tooling, use [SECURITY.md](SECURITY.md) instead.

## Changing the studio

Test a change with the keyboard, at 200% zoom, and with at least one screen reader. Add an accessible name when you add an icon-only button. Do not claim WCAG conformance unless you tested it.
