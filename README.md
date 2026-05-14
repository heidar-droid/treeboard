# Treeboard

A cinematic pyramid visualiser for any directory on disk.

## Install

```bash
pip install treeboard
```

## Use

```bash
treeboard ~/some/dir
treeboard . --no-gitignore --include-dotfiles
treeboard ~/myproject --port 9000 --no-browser
```

Opens your browser to a local URL where you can:

- Pan with the trackpad, zoom with Cmd-scroll or pinch
- Single-click pills to smart-zoom
- Double-click files to open a tethered popover with rendered content
- Drag popovers anywhere on the infinite canvas
- ⌘K to fuzzy-find any file
- ⌘0 to reset to overview
- Right-click for context menu (Reveal in Finder, Copy path, Open in editor)

## Renders

| Type | Behaviour |
|---|---|
| `.md` | Formatted prose |
| Code | Tokyo Night Storm syntax highlighting |
| `.env` | Masked key/value with REVEAL toggle |
| Images | Native |
| `.pdf` | Inline preview |
| `.csv` | Table |
| `.html` | Rendered preview |

## License

MIT
