# CLAUDE.md — working notes for future edits

## What this project is

*Sudden Day* is a 16-track concept album grounded in a single primary source: the *Nauvoo Expositor*, June 7, 1844. The repo holds:

1. The album plan and long-form essays (`ALBUM_PLAN.md`, `essays/`) — source of truth.
2. A Hugo website (`website/`, PaperMod theme) that is *generated* from the essays.

## Source of truth

- **`essays/track-NN-<slug>.md`** — one file per track. This is where lyrics, source quotes, and producer notes live.
- **`essays/intro-before-you-listen.md`**, **`album-analysis.md`**, **`epilogue-1890.md`**, **`afterword-after-you-listen.md`** — long-form companion pieces.
- **`ALBUM_PLAN.md`** — the top-level production guide (from the original snippet description).

Do **not** hand-edit `website/content/`. It is regenerated.

## Regenerate the site

```
python3 scripts/build_hugo_content.py
```

The script parses each track essay for its header (`# TITLE`, `## Track N - Act R: ...`), pulls caption/style/role out of the `**Label:** value` lines, and writes Hugo-friendly frontmatter.

## Editing a track

1. Edit `essays/track-NN-<slug>.md` — keep the heading and `**Title:** / **Caption:** / **Style:** / **Runtime Target:**` block intact; the generator parses them.
2. Run `python3 scripts/build_hugo_content.py`.
3. `cd website && hugo server` to preview.

## Don't invent history

The album's entire premise is fidelity to the primary source. Never add a source quote that isn't in the *Nauvoo Expositor* (or a directly cited contemporary document). When a lyric is implied rather than verbatim, say so in the lyric-to-source mapping table.

## Audio

`songs/` is reserved for audio files. The track pages expect (but do not require) an mp3 at `website/static/audio/track-NN-<slug>.mp3`. When those exist, the build script can be extended to embed a player shortcode — not wired up yet.

## Companion essay gap

`essays/companion-essay.md` is missing because GitLab personal-snippet file uploads can't be fetched with a personal access token. See `README.md` for how to drop it in when available.
