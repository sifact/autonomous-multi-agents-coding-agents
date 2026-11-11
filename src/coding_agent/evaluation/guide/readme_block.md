# readme_block.py

Keeps the measured results in a marked block of the README.

- The block lives between `<!-- RESULTS:START -->` and `<!-- RESULTS:END -->`; `replace_block` swaps only the text between them.
- Replacing is idempotent: the same table always gives byte-identical README text, because the report has no timestamps of its own.
- With no markers at all it creates a `## Results` section just before `## Status` (or at the end of the file) holding the block.
- Exactly one start marker followed by one end marker is accepted; a lone, reversed or duplicated marker raises `ReadmeMarkerError` and nothing is written.
- `write_readme_block` writes a temp file in the same directory, copies the file mode and renames it over the README, so an interrupted write never leaves a half-written file.
