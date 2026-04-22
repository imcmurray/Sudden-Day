# Sudden Day

*Songs from the Nauvoo Expositor* — a 16-track song cycle drawn directly from the June 7, 1844 *Nauvoo Expositor*, and a Hugo website documenting the story, the lyrics, and their source material.

Sibling project: [Journal of Discords](https://github.com/imcmurray/Journal-of-Discords) ([site](https://journalofdiscords.com/)) — same method, applied to the 26-volume *Journal of Discourses* (1854–1886).

## Repo layout

```
.
├── ALBUM_PLAN.md            Top-level album plan & production guide (from source snippet).
├── essays/                  Canonical long-form source files — one per track + intro/analysis/epilogue/afterword.
│   ├── intro-before-you-listen.md
│   ├── album-analysis.md
│   ├── track-01-june-7-1844.md … track-16-sudden-day.md
│   ├── epilogue-1890.md
│   ├── afterword-after-you-listen.md
│   └── companion-essay.md
├── scripts/
│   └── build_hugo_content.py   Regenerates website/content/ from essays/.
├── songs/                   Reserved for finished audio assets (mp3/wav) as tracks are recorded.
├── sources/                 Reserved for primary-source scans / transcripts of the Expositor.
└── website/                 Hugo site (PaperMod theme).
    ├── hugo.toml
    ├── content/             Generated from essays/ by scripts/build_hugo_content.py.
    └── themes/PaperMod/
```

## Source of truth

The `essays/` directory is the single source of truth for site content. Every track page, every act page, and every long-form essay on the site is regenerated from there by `scripts/build_hugo_content.py`.

Edit `essays/*.md`, re-run the script, and rebuild.

## Build the site

```bash
# one-time: generate content from essays
python3 scripts/build_hugo_content.py

# dev loop
cd website && hugo server
# → http://127.0.0.1:1313/

# production build
cd website && hugo --minify
# output in website/public/
```

## Source

Everything on the site traces to:

> *Nauvoo Expositor*, Vol. 1, No. 1 — Friday, June 7, 1844 — Nauvoo, Illinois.

Full text: <https://www.fairlatterdaysaints.org/answers/Primary_sources/Nauvoo_Expositor_Full_Text>

> “The remedy can never be applied, unless the disease is known.”
