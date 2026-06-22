
The app is built with:
- Python as the application shell, data layer, file I/O, and window lifecycle
- HTML + CSS + JavaScript for the tier-list UI, drag-and-drop behavior, layout, and interaction
- Optional embedded web view or browser-based UI, depending on the chosen architecture

A tier list here means a draggable ranking board where items are grouped into named tiers such as S, A, B, C, D, and F. The default goal is to let users create, edit, reorder, save, and load tier lists easily.

## Working principles
- Keep the project local-first and simple.
- Prefer small, focused changes over large rewrites.
- Preserve existing behavior unless a change is explicitly requested.
- Keep Python logic thin: startup, persistence, data validation, and communication with the UI.
- Keep UI behavior in HTML/CSS/JS, not in Python unless there is a strong reason.
- Do not add dependencies unless they clearly solve a real problem.
- If a dependency is added, document why it is needed.
- Do not break backward compatibility of saved tier-list files without a migration path.
- Use clear names for tiers, items, templates, and saved boards.
- Favor readable code over clever code.

## Dev environment tips
- Check the repository structure before editing anything.
- Find the main Python entry point first.
- Find the UI root file or folder before changing frontend behavior.
- If the project has a virtual environment, use it.
- If the project uses a lock file, keep it in sync with the chosen package manager.
- Keep assets, templates, scripts, and data files in their expected folders.
- When in doubt, inspect the existing project layout instead of inventing a new one.

## UI and product rules
- The UI should feel like a real tier-list editor, not just a static table.
- Tiers should support drag-and-drop items.
- Items should be movable between tiers and reorderable within a tier.
- The interface should support adding, removing, renaming, and clearing items.
- The user should be able to create a new tier list, save it, load it, and export it.
- Default tiers should be easy to edit.
- Keep the layout clean and readable.
- Support mouse interaction first; keyboard support is a plus if it fits naturally.
- Use responsive layout where practical.
- Avoid hard-coded dimensions unless they are needed for a stable editor feel.

## Python rules
- Use Python for app startup, data models, serialization, persistence, and integration glue.
- Keep UI state and business rules consistent between Python and JavaScript.
- Use type hints where they improve clarity.
- Prefer standard library solutions when they are enough.
- Handle file errors cleanly.
- Validate loaded data before using it.
- If a save format changes, keep compatibility in mind.

## JavaScript rules
- Keep drag-and-drop logic robust and simple.
- Avoid spaghetti event handlers.
- Separate rendering, state updates, and user actions where possible.
- Keep DOM updates predictable.
- Do not duplicate state across too many places.
- If the UI state changes, make sure the rendered view is refreshed correctly.
- Use defensive checks around missing elements and malformed data.

## CSS rules
- Keep the layout easy to scan.
- Make the tier rows visually distinct.
- Use spacing and contrast to support quick ranking and editing.
- Avoid unnecessary style complexity.
- Keep reusable classes for tier rows, item cards, buttons, dialogs, and panels.

## Data format rules
- Tier-list data must be stable, portable, and easy to save.
- Prefer a simple structured format such as JSON unless the project already uses something else.
- Store:
  - tier list title
  - tier definitions and order
  - item list
  - item placement
  - optional notes, colors, or template metadata
- Keep schema changes small and intentional.
- When changing data structure, update load/save code together.

## Testing instructions
- Add or update tests for any behavior you change.
- Test the data layer separately from the UI where possible.
- Make sure save/load round-trips still work.
- Check drag-and-drop behavior after touching the UI.
- Check tier creation, item movement, item deletion, tier deletion, and export.
- Check that malformed saved files fail safely instead of crashing the app.
- If there is an existing test runner, run the full test suite before finishing.
- If there is no test suite yet, add at least basic tests for the core data model and serialization.

## Manual verification checklist
- App starts without errors.
- A new tier list can be created.
- Items can be added.
- Items can be dragged between tiers.
- Items can be reordered inside one tier.
- Tiers can be renamed.
- Tiers can be added and removed.
- The tier list can be saved and loaded again.
- Export output matches what the user sees.
- The interface still works after refresh or restart.

## PR instructions
- Keep pull requests small and focused.
- Title format: [tier-list-editor] <Title>
- Summarize the behavior change, not just the files changed.
- Mention any save-format or compatibility impact clearly.
- Include test results or manual verification notes.
- Do not merge UI changes without checking that the editor still behaves correctly.

## Restrictions
- Do not rewrite the whole project unless explicitly asked.
- Do not change the file format casually.
- Do not remove existing functionality unless it is being replaced on purpose.
- Do not introduce framework bloat for a small desktop/editor app.
- Do not assume a specific windowing library unless the repository already uses one.
- If the project already has a chosen UI stack, follow it instead of swapping stacks.