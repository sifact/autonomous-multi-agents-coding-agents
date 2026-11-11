# readme_block.py

Keeps the measured results in a marked block of the README.

- The block lives between `<!-- RESULTS:START -->` and `<!-- RESULTS:END -->`; a marker counts only when it is alone on its line, indented at most 3 spaces, and outside a ``` or ~~~ code fence, so quoted, indented or example markers are ignored; an unclosed fence is refused so a section is never appended inside it.
- With no markers it creates a `## Results` section just before `## Status` (or at the end); exactly one start followed by one end is replaced, and a lone, reversed or duplicated marker raises `ReadmeMarkerError` with nothing written.
- The file is read and written as bytes and the block uses the file's own newline style, so a CRLF README stays CRLF and the text outside the block is byte-identical.
- Replacing is idempotent: the same table always gives the same README, because the report has no timestamps of its own.
- A symlinked README is written through to its target and stays a link; the write goes to a temp file beside the target, copies the mode and renames over it, so an interrupt never leaves half a file.
