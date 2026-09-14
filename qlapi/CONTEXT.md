# Label Editor

The browser-based editor for laying out and printing Brother QL labels: a canvas-based design surface, a template system for reusable layouts with fillable fields, and an upload path for printing existing files directly.

## Language

**Label**:
A single print job's artwork, sized to a physical tape/die-cut spec (width fixed, length fixed or endless). Either freely designed on the canvas or produced by filling a Template.
_Avoid_: Design, page

**Template**:
A saved canvas layout containing zero or more Placeholders. Templates are the only place Placeholders may exist — a Label printed directly from Design mode never has them.
_Avoid_: Layout, design (as a saved noun)

**Placeholder**:
A canvas object inside a Template marked as fillable (text, image, or barcode). Keeps its position/size; filling replaces its content only. Only creatable/editable while in Template edit mode.
_Avoid_: Slot, field (slot is the internal prop name; placeholder is the user-facing term)

**Design mode**:
The default workspace state: a blank or freely-edited canvas for a one-off Label, no Placeholders, printed as-is.

**Template edit mode**:
The workspace state entered via a Template's **Edit** action or **New template**. Canvas becomes editable, Placeholder tools (Make placeholder, slot kinds) appear, Save writes back to that Template. New template starts from whatever is currently on the canvas (or blank).

**Fill mode**:
The workspace state entered by clicking anywhere on a Template row except its Edit/Delete actions. Loads that Template's canvas locked (objects fixed, no Placeholder tools) and opens the Fill panel to type values into its Placeholders, then preview/print.

**Fill panel**:
The docked side panel (not a modal) used only in Fill mode to enter Placeholder values. Collapses to a chevron sliver when closed without leaving Fill mode; pushes the stage over rather than overlaying it.

## Flagged ambiguities

- File-mode length label: computed per page (from that page's own aspect ratio scaled to tape width), not just the first page — a multi-page PDF can have pages of different lengths. The label tracks whichever page is currently in view.

- The code's internal prop/variable names (`slot`, `templateMode`, `fileMode`) predate this glossary and don't need renaming, but new UI copy and docs should say Placeholder/Template edit mode/Design mode per above.

## Example dialogue

> **Dev**: Should the upload-a-file path get Template support too?
> **Domain expert**: No — Templates and Placeholders only exist for canvas-designed Labels. An uploaded file just prints as-is.
>
> **Dev**: If I click a Template in the list, what happens?
> **Domain expert**: That's Fill mode — canvas loads locked, Fill panel opens beside it. If you meant to change the layout, use Edit instead, which puts you in Template edit mode.
