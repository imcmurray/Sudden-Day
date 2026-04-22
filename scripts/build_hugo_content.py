#!/usr/bin/env python3
"""
Generate Hugo content under website/content/ from the canonical essays/
directory. Rerun any time the essays change.

Source of truth layout:
  essays/
    intro-before-you-listen.md
    album-analysis.md
    track-01-june-7-1844.md ... track-16-sudden-day.md
    epilogue-1890.md
    afterword-after-you-listen.md
    companion-essay.md  (optional; dropped in by user)

Generates:
  website/content/_index.md              (home)
  website/content/about.md
  website/content/about/source.md
  website/content/tracks/_index.md
  website/content/tracks/<slug>.md       (one per track)
  website/content/acts/_index.md
  website/content/acts/act-<roman>.md    (one per act, describing it)
  website/content/essays/_index.md
  website/content/essays/<slug>.md
"""
from __future__ import annotations
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ESSAYS = REPO / "essays"
SITE = REPO / "website" / "content"

ACTS = {
    "I":   {"title": "Act I — The Awakening",     "subtitle": "The whistleblowers find their voice", "tracks": [1, 2, 3]},
    "II":  {"title": "Act II — The Women",        "subtitle": "The hidden victims speak",            "tracks": [4, 5, 6, 7]},
    "III": {"title": "Act III — The Revelations", "subtitle": "What was taught in secret",           "tracks": [8, 9, 10]},
    "IV":  {"title": "Act IV — The Power",        "subtitle": "The machinery of control",            "tracks": [11, 12, 13]},
    "V":   {"title": "Act V — The Reckoning",     "subtitle": "The silencing that wasn't",           "tracks": [14, 15, 16]},
}

# Suno embed UUIDs per slug. Resolved from user-supplied /s/<shortid> share URLs
# by following the 307 redirect to /song/<uuid>. Embeds live at
# https://suno.com/embed/<uuid>.
#
# NOTE: "citizens-of-hancock-county" is tentatively mapped to the user's
# "THE RECKONING" link — it's the only album track missing from the user's
# list, and Act V is titled "The Reckoning". If that assumption is wrong,
# swap the UUID below.
SUNO_UUIDS = {
    "june-7-1844":               "fcb8d616-61f5-448d-bd4a-847c23677b7d",
    "forbearance":               "cc51bd8c-695e-4536-9b3f-2135543650e4",
    "seven-wives":               "86691f97-49c0-4c6a-b492-6cbcb5570ea2",
    "ten-thousand-miles":        "8e147196-5f20-463d-8ddd-d0577b9ba69c",
    "positively-no-admittance":  "c54441ec-b558-4552-ba54-5c1089cf9867",
    "the-tender-tree":           "febfa13b-8e0f-4d8f-b149-f6c10e4d2018",
    "under-condemnation":        "a5f0bd5e-7d83-4b7d-8bbf-2353edaa9d13",
    "the-revelation":            "e8fc7980-ad1b-4367-b20e-a067dc1a131f",
    "many-gods":                 "a5ca0607-8880-4fee-89e6-d22566a8db2c",
    "the-great-throat":          "b81dd2e3-fdfb-4a2a-930e-574f75754cec",
    "king-and-lawgiver":         "10228a53-bc0e-443f-89f5-0768105a323d",
    "the-inquisition":           "037ee37d-c35d-453d-9a8b-df2d295b00fd",
    "habeas-corpus":             "f38f731a-e341-4420-88cb-e5f696dbce96",
    "citizens-of-hancock-county": "ff4ea206-0d85-4071-83ef-84d2f9ba8d51",
    "the-burning":               "299d3f95-ab0a-44b3-9c9d-f38443f07865",
    "sudden-day":                "d8a6d046-e086-4e8a-b636-a2b1f6577907",
}
SUNO_UUIDS_ESSAY = {
    "epilogue-1890": "ba50afac-5de3-4cc0-b5fc-041906cb35b3",
}

def suno_url(uuid: str) -> str:
    return f"https://suno.com/embed/{uuid}"


@dataclass
class Track:
    number: int
    slug: str
    title: str
    act_roman: str
    caption: str = ""
    style: str = ""
    role: str = ""
    runtime: str = ""
    body: str = ""


def parse_track(path: Path) -> Track:
    """Extract track metadata from an essay file.

    Essays follow the pattern:
      # TITLE
      ## Track N - Act R: NAME
      ...
      **Title:** ...
      **Caption:** ...
      **Style:** `...`
      **Runtime Target:** ...
    """
    text = path.read_text()
    m = re.match(r"# (.+?)\n## Track (\d+) - Act ([IVX]+):", text)
    if not m:
        raise ValueError(f"Could not parse track header in {path.name}")
    display_title, track_num, act_roman = m.groups()

    def find(label: str) -> str:
        mm = re.search(rf"\*\*{re.escape(label)}:\*\*\s*(.+)", text)
        return mm.group(1).strip() if mm else ""

    title = find("Title") or display_title.strip().title()
    caption = find("Caption")
    style = find("Style").strip("`").strip()
    role = find("Role")
    runtime = find("Runtime Target")

    # Slug from filename: "track-01-june-7-1844.md" -> "june-7-1844"
    slug = re.sub(r"^track-\d+-", "", path.stem)

    return Track(
        number=int(track_num),
        slug=slug,
        title=title,
        act_roman=act_roman,
        caption=caption,
        style=style,
        role=role,
        runtime=runtime,
        body=text,
    )


def quote(s: str) -> str:
    """Quote a string safely for TOML frontmatter."""
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def frontmatter(fields: dict) -> str:
    lines = ["+++"]
    for k, v in fields.items():
        if isinstance(v, list):
            items = ", ".join(quote(str(x)) for x in v)
            lines.append(f"{k} = [{items}]")
        elif isinstance(v, bool):
            lines.append(f"{k} = {str(v).lower()}")
        elif isinstance(v, int):
            lines.append(f"{k} = {v}")
        else:
            lines.append(f"{k} = {quote(str(v))}")
    lines.append("+++\n")
    return "\n".join(lines)


def roman_slug(roman: str) -> str:
    return f"act-{roman.lower()}"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"  wrote {path.relative_to(REPO)}")


def strip_source_footer(body: str) -> str:
    """Remove the trailing '*"The remedy..."* — Nauvoo Expositor' footer that
    every per-track essay ends with. Anchored to end-of-string so it only
    strips the final occurrence and never consumes mid-document content."""
    return re.sub(
        r"\n+---\n+\*\"The remedy can never be applied[^\n]*\n[^\n]*Nauvoo Expositor[^\n]*\n*\Z",
        "\n",
        body,
    )


def build_home() -> None:
    content = frontmatter({"title": "Sudden Day"}) + """\
*Sudden Day: Songs from the Nauvoo Expositor* is a 16-track song cycle drawn directly from the June 7, 1844 *Nauvoo Expositor* — the single-issue newspaper destroyed by Joseph Smith three days after it was printed. Every lyric traces to the primary source.

## The Structure

- **[Act I — The Awakening](/acts/act-i/)** · The whistleblowers find their voice
- **[Act II — The Women](/acts/act-ii/)** · The hidden victims speak
- **[Act III — The Revelations](/acts/act-iii/)** · What was taught in secret
- **[Act IV — The Power](/acts/act-iv/)** · The machinery of control
- **[Act V — The Reckoning](/acts/act-v/)** · The silencing that wasn't

[Browse all tracks →](/tracks/) &nbsp;·&nbsp; [Read the essays →](/essays/) &nbsp;·&nbsp; [About the source document →](/about/source/)

---

> “The remedy can never be applied, unless the disease is known.” — *Nauvoo Expositor*, June 7, 1844
"""
    write(SITE / "_index.md", content)


def build_about() -> None:
    content = frontmatter({"title": "About This Project"}) + """\
## What is the *Nauvoo Expositor*?

The *Nauvoo Expositor* was a four-page broadsheet newspaper, Volume 1, Number 1, published on Friday, **June 7, 1844** in Nauvoo, Illinois. There would never be a Number 2.

**Publishers:** Not outsiders. Not enemies from without. The paper was printed by **William Law** — then Second Counselor in the First Presidency of the LDS Church, one of Joseph Smith's two closest advisors — together with his brother **Wilson Law** (Brigadier General of the Nauvoo Legion), **Jane Law** (William's wife), **Robert D. Foster** (Nauvoo surgeon and Justice of the Peace), **Charles A. Foster**, **Francis M. Higbee**, **Chauncey L. Higbee**, and **Charles Ivins**.

**Contents:** A Preamble, 15 Resolutions, sworn affidavits by William Law, Jane Law, and Austin Cowles, Francis Higbee's "Citizens of Hancock County" letter, and editorial content exposing specific abuses — plural marriage taught in secret and denied in public, theological innovation (a "plurality of Gods" doctrine), financial exploitation of the gathering, the fusion of church and civic power, and the extra-judicial treatment of dissenters.

**Destroyed on June 10, 1844** — three days after publication — by order of Joseph Smith, acting as Mayor of Nauvoo. The marshal and a posse of roughly 100 men removed the press, scattered the type, and burned the remaining copies. **Seventeen days later**, Joseph Smith was killed at Carthage Jail.

---

## Then and now

When the *Expositor* printed, its central factual claims were denied. Today, the LDS Church itself confirms most of them:

| The *Expositor* said (1844) | The Church now says |
|---|---|
| Joseph Smith has multiple plural wives. | Joseph had 30–40 plural wives, including a 14-year-old and women married to other living men.¹ |
| Plural marriage is taught in secret and denied in public. | Leaders issued "carefully worded denials" while practicing it.¹ |
| A plural-marriage revelation has been read to the High Council. | That revelation is canonized as **D&C 132**. |
| Joseph has been received as king and lawgiver. | The Council of Fifty voted on April 11, 1844 to receive him "as our Prophet, Priest & King."² |
| The plurality-of-gods doctrine is being taught. | Publicly preached at general conference on April 7, 1844 — the King Follett Discourse. |
| Plural marriage should be ended. | Officially ended by the 1890 Manifesto (Official Declaration 1). |

*¹ [*Plural Marriage in Kirtland and Nauvoo* — Gospel Topics Essay, 2014](https://www.churchofjesuschrist.org/study/manual/gospel-topics-essays/plural-marriage-in-kirtland-and-nauvoo?lang=eng). &nbsp; ² [Joseph Smith Papers — Council of Fifty Minutes](https://www.josephsmithpapers.org/articles/administrative-records-council-of-fifty-minutes).*

---

## Why this project exists

The *Expositor* was destroyed in three days. Its testimony has lasted 180 years. This project exists because the single most documented act of whistleblowing in early LDS history — printed by the most senior possible insider — is largely absent from modern Latter-day Saint discourse. When the Church's 2013 "Race and the Priesthood" essay and 2014 "Plural Marriage" essay acknowledged things the *Expositor* had said in 1844, the *Expositor* itself was not named. The publishers were not credited. The women whose sworn affidavits first put these facts on the record were not restored to the historical account.

*Sudden Day* is an attempt to restore them — not by adding commentary, but by letting their own words carry the story.

---

## What you'll find here

- **[Tracks](/tracks/)** — Every song with lyrics, source quotes, a lyric-to-source mapping, and producer notes.
- **[Acts](/acts/)** — The five-act arc of the album with the tracks that belong to each.
- **[Essays](/essays/)** — Long-form companion pieces: *Before You Listen*, the album analysis, the 1890 epilogue, *After You Listen*, and the companion essay.
- **[Source document](/about/source/)** — The *Nauvoo Expositor* itself, and a reply to the apologetic framing.
- **[Methodology](/methodology/)** — How the songs were constructed and what our quality bar is.
- **[Our Mission](/mission/)** — Why this project exists, what it is not, and the generational harm it seeks to acknowledge.
- **[FAQ](/faq/)** — Common questions, including "is this anti-Mormon?" and "isn't this just quote mining?"

---

## Method, in one paragraph

Lyrics are constructed from the *Expositor's* exact words wherever possible. Where a lyric is implied or paraphrased, the **lyric-to-source mapping** on each track page shows the derivation. We do not invent history. We do not quote out of context to change meaning. We acknowledge charitable readings before rejecting them. The publishers' words and the women's sworn testimony do the heavy lifting; the music only makes them hard to forget.

---

## Companion project

*Sudden Day* is a sibling project to [**Journal of Discords**](https://journalofdiscords.com/) — a song-based documentation project drawn from the 26-volume *Journal of Discourses* (1854–1886), the published sermons of early LDS leaders. Same method, different primary source: the *Expositor* captures a single 1844 inflection point; Journal of Discords traces the doctrinal and cultural aftermath across the decades that followed.

The two projects share a single thesis — *the remedy can never be applied, unless the disease is known* — and are meant to be read together.

---

> *"The remedy can never be applied, unless the disease is known."*
> — *Nauvoo Expositor*, June 7, 1844
"""
    write(SITE / "about" / "_index.md", content)
    source = frontmatter({"title": "Source Document"}) + """\
The primary source for the entire album is:

**Nauvoo Expositor** — Volume 1, Number 1 · Friday, June 7, 1844 · Nauvoo, Illinois

Four-page broadsheet. Single issue. Destroyed by order of Joseph Smith three days after publication.

## Contents of the issue

- **Preamble** — the publishers' statement of purpose and the album's thesis: *"The remedy can never be applied, unless the disease is known."*
- **Resolutions (1–15)** — public positions on theology, church governance, and the separation of church and state
- **Affidavits** — sworn testimony from **William Law**, **Jane Law**, and **Austin Cowles**
- **"Citizens of Hancock County"** — Francis M. Higbee's letter to his neighbors
- **Editorial content** — exposing specific abuses

## Full text online

The full text of the Expositor is preserved at:

<https://www.fairlatterdaysaints.org/answers/Primary_sources/Nauvoo_Expositor_Full_Text>

## Publishers

- **William Law** — Second Counselor in the First Presidency
- **Wilson Law** — Brigadier General, Nauvoo Legion
- **Jane Law** — William's wife; sworn affidavit included
- **Robert D. Foster** — Nauvoo surgeon and Justice of the Peace
- **Charles A. Foster** — Robert's brother
- **Francis M. Higbee** — Former missionary, author of "Citizens of Hancock County"
- **Chauncey L. Higbee** — Francis's brother
- **Charles Ivins** — High Priest

These were not outsiders. They were the inner circle. They knew everything.

---

## Why this document still matters today

LDS apologists — most visibly **FAIR Latter-day Saints** — have published responses that frame the *Expositor* as unreliable, legally addressable, or doctrinally misrepresentative. Here are their strongest arguments, stated as they state them, followed by the reasons the document's testimony still holds up 180 years later.

### The apologetic case against the Expositor

- **"The destruction was lawful, or nearly so."** The Nauvoo City Council — which included non-Mormons — unanimously declared the paper a public nuisance, and under pre-Fourteenth-Amendment common law, municipal abatement of a libelous nuisance was a recognized remedy. Joseph Smith offered to pay damages.
- **"Invoking the First Amendment is anachronistic."** In 1844 the Bill of Rights constrained only the federal government; it was not incorporated against the states until after 1868.
- **"Anti-press mob violence was a real threat in Illinois."** The council's action is framed as defensive policy in a volatile environment with roughly sixteen episodes of anti-press violence between 1832 and 1867, including the 1833 destruction of the LDS *Evening and Morning Star* in Missouri.
- **"The publishers were embittered apostates with personal axes to grind."** William Law's arc from calling Joseph "honest and honourable" (1836) to "demon in human shape" (1844) is attributed to rejection of the plural-marriage revelation Hyrum showed him, land-investment disputes in Nauvoo, and grief after family deaths.
- **"The tone was inflammatory, not journalistic."** The *Expositor* is characterized as a polemical escalation rather than a news account; phrases like "blood thirsty and murderous demon in human shape" are cited as evidence the paper was not written in good faith.
- **"Specific accusations fail on the facts."** On the "plurality of gods" charge, FAIR notes that Joseph's King Follett remarks "were not published until after his death," no verbatim transcript exists, and the doctrine "is not clear, and mostly speculative."

### Why the document still matters

- **An LDS apostle has already conceded the destruction was illegal.** In a 1965 *Utah Law Review* article, legal scholar **Dallin H. Oaks** — later a member of the Quorum of the Twelve and the First Presidency — concluded that while a municipality could arguably abate printed copies of a libelous paper, *the destruction of the press and type was not legally defensible under 1844 law.* The single most consequential act in the chain of events — the one the *Expositor* exists to document — was unlawful by the analysis of a future senior church leader. [Oaks, "The Suppression of the Nauvoo Expositor," 9 Utah L. Rev. 862 (1965)](https://dc.law.utah.edu/ulr/vol9/iss4/2/)

- **The Church itself now confirms the Expositor's central factual claim about plural marriage.** The 2014 Gospel Topics essay *Plural Marriage in Kirtland and Nauvoo* acknowledges that Joseph Smith married roughly 30–40 women, including a 14-year-old (Helen Mar Kimball) and women already married to other living men. These are facts the *Expositor* alleged and that Joseph publicly denied. [*Plural Marriage in Kirtland and Nauvoo* — Gospel Topics Essay](https://www.churchofjesuschrist.org/study/manual/gospel-topics-essays/plural-marriage-in-kirtland-and-nauvoo?lang=eng)

- **The Church also acknowledges the public denials were deliberate.** The same essay concedes leaders issued "carefully worded denials that denounced spiritual wifery and polygamy but were silent about what Joseph Smith and others saw as divinely mandated 'celestial' plural marriage." That is exactly the pattern — *taught secretly, and denied openly* — that the *Expositor* identified as the core grievance.

- **Austin Cowles's affidavit is corroborated by canonized LDS scripture.** Cowles swore in May 1844 that Hyrum Smith read a revelation on plural marriage to the Nauvoo High Council. That revelation is now canonized as [Doctrine and Covenants 132](https://www.churchofjesuschrist.org/study/scriptures/dc-testament/dc/132?lang=eng). The *Expositor* was not inventing doctrine; it was previewing a text the Church still treats as scripture.

- **The theocratic charge is confirmed by documents published by the Church's own historians.** The Joseph Smith Papers published the Council of Fifty minutes in 2016. On April 11, 1844 — two months before the *Expositor* — the Council of Fifty voted to receive Joseph Smith "as our Prophet, Priest & King." Resolution 12 of the *Expositor* ("we will not acknowledge any man as king or lawgiver to the church; for Christ is our only king and law-giver") was not paranoid. It was reporting a recent, documented event. [Joseph Smith Papers — Administrative Records, Council of Fifty Minutes](https://www.josephsmithpapers.org/articles/administrative-records-council-of-fifty-minutes)

- **The "plurality of gods" charge maps onto a sermon 20,000 people had already heard.** Joseph Smith delivered the King Follett Discourse at general conference on **April 7, 1844** — two months before the *Expositor* — teaching that God was once a man and that "the head one of the Gods brought forth the Gods." The paper was reporting a public sermon, not fabricating exotic doctrine.

- **Plural marriage eventually ended — which is the dissenters' position.** The 1890 Manifesto formally halted the practice the publishers of the *Expositor* had objected to in 1844. In outcome, the institutional Church arrived where William Law and the others stood on the day they printed the paper. [Official Declaration 1](https://www.churchofjesuschrist.org/study/scriptures/dc-testament/od/1?lang=eng)

### The thesis

The *Expositor*'s value is not rhetorical tone. It is evidentiary. Its central factual claims — that plural marriage was being practiced and publicly denied, that a plurality-of-gods doctrine was being taught, that Joseph had been received as "Prophet, Priest & King," that a secret council was acting beyond the civil and ecclesiastical order — have all been corroborated by primary sources the Church itself now publishes. The paper was destroyed in three days. The testimony has lasted 180 years.

> *"Men solace themselves by saying the facts slumber in the dark caverns of midnight. But Lo! it is sudden day, and the dark deeds of foul fiends shall be exposed from the house-tops."* — *Nauvoo Expositor*, June 7, 1844
"""
    write(SITE / "about" / "source.md", source)


def build_tracks_index() -> None:
    content = frontmatter({"title": "Tracks"}) + """\
Every track on *Sudden Day*, in album order. Each page carries the lyrics, the source quotes from the *Nauvoo Expositor*, a line-by-line lyric-to-source mapping, and producer notes.
"""
    write(SITE / "tracks" / "_index.md", content)


def build_acts_index() -> None:
    content = frontmatter({"title": "Acts"}) + """\
The album is built as five acts, each a movement in the story.
"""
    write(SITE / "acts" / "_index.md", content)


def build_act_pages(tracks: dict[int, Track]) -> None:
    for roman, info in ACTS.items():
        lines = [frontmatter({"title": info["title"]})]
        lines.append(f"*{info['subtitle']}*\n")
        for n in info["tracks"]:
            t = tracks[n]
            lines.append(f"### [Track {t.number:02d} — {t.title}](/tracks/{t.slug}/)")
            if t.caption:
                lines.append(f"> {t.caption}")
            lines.append("")
        write(SITE / "acts" / f"{roman_slug(roman)}.md", "\n".join(lines))


def build_track_pages(tracks: dict[int, Track]) -> None:
    for t in tracks.values():
        body = strip_source_footer(t.body)
        # Drop the duplicate first two heading lines; Hugo will render frontmatter title.
        body = re.sub(r"^# .+?\n## Track \d+ - Act [IVX]+:[^\n]*\n### From[^\n]*\n+---\n+", "", body, count=1)
        fm_fields = {
            "title": f"Track {t.number:02d} — {t.title}",
            "linkTitle": t.title,
            "description": t.caption,
            "summary": t.caption,
            "weight": t.number,
            "acts": [ACTS[t.act_roman]["title"]],
            "tags": [s.strip() for s in t.style.split(",") if s.strip()][:8] if t.style else [],
        }
        uuid = SUNO_UUIDS.get(t.slug)
        if uuid:
            fm_fields["suno_url"] = suno_url(uuid)
        fm = frontmatter(fm_fields)
        # Inject the Suno player at the top of the body so it sits above the
        # song overview section on the rendered page.
        prefix = "{{< suno >}}\n\n" if uuid else ""
        write(SITE / "tracks" / f"{t.slug}.md", fm + prefix + body)


def build_mission() -> None:
    content = frontmatter({"title": "Our Mission"}) + """\
## We do not endorse what this album documents

Let us be clear: **we do not endorse the coercion, theological manipulation, financial exploitation, or extra-judicial power documented in the *Nauvoo Expositor*.** We do not endorse the abuse of the women whose affidavits the paper carried. We document these things because they happened, because contemporaneous insiders swore to them, and because the historical record deserves to be preserved rather than quietly revised.

Nothing on this site is invented. Every claim ties to the *Expositor*'s own words, to contemporary sources, or to the LDS Church's own later acknowledgments.

---

## What the *Nauvoo Expositor* was

The *Expositor* was not a pamphlet by hostile outsiders. It was a newspaper printed by the **Second Counselor in the First Presidency**, together with his wife, his brother (a Brigadier General in the Nauvoo Legion), a Justice of the Peace, a High Priest, and other high-ranking members who had seen the movement from the inside. They staked their reputations and their lives on a single issue:

> *"We are aware, however, that we are hazarding every earthly blessing, particularly property, and probably life itself, in striking this blow at tyranny and oppression."* — *Nauvoo Expositor*, Preamble

Three days later, the press was destroyed. Seventeen days after that, Joseph Smith was killed at Carthage. The publishers had been correct about the cost.

---

## The generational impact

The publishers of the *Expositor* did not write in the abstract. The affidavits they carried described specific women — including the publisher's own wife — facing a theological bind that still shapes the Latter-day Saint community 180 years later:

- **Women were told** that a refusal to share their husbands would place them "under condemnation before God" (Jane Law's affidavit).
- **Young women were approached** in rooms that bore the warning "*Positively NO Admittance*" and bound by oaths under "penalty of death" never to speak of what was revealed to them.
- **Wives already sealed** were sent away "until all is well," to return "as from a long visit," while doctrine, guilt, and silence did their work.

When the *Expositor* published and was destroyed, these women's testimony was destroyed with it — or so it was meant to be. In fact the paper survived, and the testimony it carried remains the earliest contemporaneous primary source documenting what Nauvoo polygamy looked like from the inside. The 2014 *Plural Marriage in Kirtland and Nauvoo* Gospel Topics essay, a century and a half later, confirms the substance of what the women of the *Expositor* swore in 1844.

The harm done to those women was real. The harm passed down through generations of silence was real. The people who were harmed by these practices deserve to have their experience acknowledged, not footnoted out of the modern narrative.

---

## Why we document

Today, it is difficult for a curious Latter-day Saint to find a straightforward summary of what the *Expositor* actually said. The paper is most often referenced in terms of the *legality of its destruction*, not the substance of its reporting. The publishers are most often described as "apostates" or "dissenters," not as the most senior insiders in the movement — which is what they were.

We believe in accountability. We believe that:

- **History should not be sanitized** to avoid discomfort.
- **Those who were harmed deserve to have that harm acknowledged** by name, not by hint.
- **Future generations deserve to know what was actually taught and practiced** before 1844, not just what was later disavowed.
- **The primary source should be accessible** — and, where possible, memorable.

Songs are memorable. That is the entire reason this project is a song cycle rather than an essay collection. The *Expositor*'s words rhyme and scan because they were written to be heard. We only had to set them to music.

---

## For those affected

If your family line runs through 19th-century Nauvoo; if your experience of the modern Church has been shaped by quiet half-knowledge of what happened there; if you grew up hearing that the *Expositor* was "just bitterness from apostates" and you now find that it largely told the truth — this site is for you too. The harm was real. The silence was real. The record matters.

---

## Our commitment

- **Accuracy.** Every quote is sourced. Every claim is documented.
- **Context.** We provide historical setting and, where relevant, the modern apologetic response.
- **Honesty.** We do not exaggerate. We do not quote out of context to change meaning.
- **Respect.** We recognize the weight of this material for those affected.

---

## Companion project: *Journal of Discords*

*Sudden Day* is part of a small family of projects documenting early Latter-day Saint history in song, each grounded in a different primary source and method.

### 🎵 [Journal of Discords](https://journalofdiscords.com/) &nbsp;·&nbsp; [source on GitHub](https://github.com/imcmurray/Journal-of-Discords)

Journal of Discords draws from the **26-volume *Journal of Discourses*** (1854–1886) — the published sermons of Brigham Young, John Taylor, Heber C. Kimball, and other early LDS leaders, delivered from the Salt Lake Tabernacle and circulated worldwide as a semi-monthly subscription publication. Where *Sudden Day* captures a single inflection point — the 1844 moment when insiders first tried to blow the whistle — Journal of Discords traces the doctrinal and cultural aftermath across the following decades: race and the priesthood ban, Adam-God, blood atonement, the escalation and eventual end of polygamy.

The two projects share a single thesis: **the remedy can never be applied unless the disease is known.** They are meant to be read together. What the *Expositor* exposed in 1844, the *Journal of Discourses* then preached, defended, and extended for another forty years.

---

> *"The remedy can never be applied, unless the disease is known."*

This project exists so that the disease is known.
"""
    write(SITE / "mission.md", content)


def build_faq() -> None:
    content = frontmatter({"title": "Frequently Asked Questions"}) + """\
## What is this project?

*Sudden Day: Songs from the Nauvoo Expositor* is a 16-track song cycle and companion website documenting the contents of a single historical newspaper — the *Nauvoo Expositor*, Volume 1, Number 1, June 7, 1844. The paper was printed by William Law (then Second Counselor in the LDS First Presidency) and seven other senior insiders, destroyed by order of Joseph Smith three days later, and has been partially vindicated by the LDS Church's own historical essays in the 21st century.

Each song grounds its lyrics in the *Expositor*'s exact words and in the sworn affidavits it carried. Every track page carries a lyric-to-source mapping.

---

## Is this anti-Mormon?

This project is not about attacking individuals or their faith. It is about historical accuracy and accountability for a specific, documented inflection point in 1844.

- We use a **primary source** exclusively (supplemented by LDS-published materials).
- We cite everything.
- We **steel-man** the apologetic response before showing why the source material holds up — see [the source document page](/about/source/).
- We **agree with the modern Church** on key points: that plural marriage was practiced (2014 Gospel Topics essay), that it was publicly denied while practiced (same essay), and that it should be ended (1890 Manifesto).

Documenting what the most senior possible insider said in 1844 — from a paper whose full text is hosted by *FAIR Latter-day Saints* itself — is not an attack on the faith. It is an attempt to restore an uncomfortable but important part of its own record.

---

## How can I verify the sources?

The *Nauvoo Expositor* is in the public domain and widely available. Recommended full-text sources:

- **[FAIR Latter-day Saints — *Nauvoo Expositor* Full Text](https://www.fairlatterdaysaints.org/answers/Primary_sources/Nauvoo_Expositor_Full_Text)** — hosted by an LDS apologetic organization, so there's no question about provenance.
- **[University of Utah — digitized original](https://collections.lib.utah.edu/details?id=196898)** — scanned from a surviving physical copy.

For the apologetic framing we respond to, see FAIR's pages on the [*Nauvoo Expositor*](https://www.fairlatterdaysaints.org/answers/Joseph_Smith_and_the_Nauvoo_Expositor), [William Law](https://www.fairlatterdaysaints.org/answers/William_Law), and the [suppression of the paper](https://www.fairlatterdaysaints.org/answers/City_of_Nauvoo/Nauvoo_Expositor/Suppression_of_the_Nauvoo_Expositor).

For the church's own subsequent admissions, see the [*Plural Marriage in Kirtland and Nauvoo*](https://www.churchofjesuschrist.org/study/manual/gospel-topics-essays/plural-marriage-in-kirtland-and-nauvoo?lang=eng) Gospel Topics essay.

---

## Why songs?

Because the *Expositor*'s words were written to be heard. The publishers were trained in the rhetoric of their era — scripture, sermon, and civic declaration — and their sentences have a natural cadence. "Forbearance has ceased to be a virtue." "Lo! the wolf is in the fold." "The remedy can never be applied, unless the disease is known." These phrases do not need a melody to be memorable, but they accept one readily, and once you have heard them sung you will not be able to unremember them.

A song also forces the kind of compression that an essay can avoid. There is no room to euphemize. When a lyric says *"robbed of that which nothing but death can restore,"* it means what the affidavit meant.

---

## Isn't this just quote mining?

Quote mining means taking a speaker's words out of context to produce a meaning they did not intend. This project does the opposite:

1. **The source is a single coherent document**, not a corpus searched for damning sentences. The *Expositor* was published as one issue with a single editorial purpose stated in its Preamble. We work from that purpose outward.
2. **Full context is provided** on every track page — the quoted passage, the surrounding section of the paper, and the historical setting.
3. **Charitable readings are addressed** — the [source document page](/about/source/) summarizes FAIR's strongest arguments for dismissing the paper and responds to each.
4. **The full text is one click away** so readers can verify everything.

If reading the full *Expositor* and the full affidavits makes the charges look *worse* rather than better, that is a property of the source, not of the method.

---

## What about the destruction of the press? Wasn't that legal under 1844 law?

This is the most common apologetic framing. It is also the one most clearly conceded by the Church's own scholars. Before he became an LDS apostle, **Dallin H. Oaks** published a 1965 *Utah Law Review* article, *The Suppression of the Nauvoo Expositor*, in which he concluded that while a municipality could arguably abate printed copies of a libelous paper, *the destruction of the press and type itself was not legally defensible under the law of the time*. See [Oaks, 9 Utah L. Rev. 862 (1965)](https://dc.law.utah.edu/ulr/vol9/iss4/2/). We address this in more detail on the [source document page](/about/source/).

---

## Who created this?

This is an independent project. It is **not affiliated with** The Church of Jesus Christ of Latter-day Saints, any ex-Mormon organization, FAIR Latter-day Saints, or any other institution.

It is a sibling project to [Journal of Discords](https://journalofdiscords.com/), which follows the same method applied to the 26-volume *Journal of Discourses* (1854–1886).

---

## Can I use this material?

The *Nauvoo Expositor* is in the public domain. Our original analysis and creative works are provided for educational purposes. If you use any of this material, please:

- Verify the primary-source citations yourself.
- Attribute this project where appropriate.
- Hold yourself to the same accuracy bar — don't reformulate these quotations into something they weren't.

---

## I found an error — what should I do?

Please tell us. We care more about being correct than about being right. Open an issue on the project's [GitHub repository](https://github.com/imcmurray/Sudden-Day) with the specific claim, the source that contradicts it, and your suggested correction.

---

## Why does this matter?

In three days in June 1844, a group of insiders printed a newspaper, the newspaper was destroyed, and the man it accused went to his death. What happened in those three days set the shape of Utah Mormonism for the next fifty years, and the shape of American Mormonism's relationship with its own history for the next century and a half.

The *Expositor* was right about almost everything it reported. The Church has since acknowledged, in its own essays, most of what its publishers staked their lives to print. They were not rewarded for being early; they were erased.

This project is an attempt to put their voices back into the record — not as curiosities, but as witnesses.

---

> *"The remedy can never be applied, unless the disease is known."* — *Nauvoo Expositor*, June 7, 1844
"""
    write(SITE / "faq.md", content)


def build_methodology() -> None:
    content = frontmatter({"title": "Methodology"}) + """\
This project follows a rigorous methodology to ensure accuracy, fairness, and intellectual honesty. We document our approach so readers can evaluate our work on its merits.

---

## Core principles

### 1. One primary source, fully worked

Every claim on this site traces to one of:

- The *Nauvoo Expositor*, Vol. 1, No. 1 — June 7, 1844, Nauvoo, Illinois.
- The sworn affidavits printed within the *Expositor* (William Law, Jane Law, Austin Cowles).
- Directly contemporaneous documents cited or quoted *by* the *Expositor* (e.g., the Nauvoo High Council minutes of April 1844, Joseph Smith's May 26, 1844 sermon).
- LDS-published materials **when used as corroboration** — the Joseph Smith Papers (Council of Fifty minutes), the canonized Doctrine and Covenants (D&C 132), and the Gospel Topics essays (2014 *Plural Marriage in Kirtland and Nauvoo*).

We do not work from secondhand characterizations or polemical summaries. If a source is later than June 1844 and was not written by the *Expositor*'s original authors, we cite it specifically and only as corroboration of what the 1844 document already said.

### 2. Let them speak

The whistleblowers, the women, and the High Council witnesses are more compelling in their own words than in ours. Where possible, lyrics are *verbatim quotations* from the Preamble, Resolutions, or affidavits. Where direct quotation does not scan, we paraphrase tightly — and mark the paraphrase on the track page's lyric-to-source mapping.

### 3. Full documentation per track

Every track page includes:

- **Complete lyrics**
- **Source material** — the *Expositor* passages that back each section
- **Lyric-to-source mapping** — a line-by-line table showing verbatim vs. paraphrased vs. implied
- **Historical context** — the setting and significance
- **Producer notes** — why this song exists and what it is trying to do

### 4. Charitable reading first

Before presenting a harsh reading, we consider the strongest sympathetic interpretation. The [source document page](/about/source/) steel-mans FAIR Latter-day Saints' best arguments for dismissing the *Expositor* before responding to each one.

If a reading exists that lets the material off the hook, we acknowledge it — then show why the source material defeats that reading.

### 5. Their own standards

We hold the publishers *and the subjects* of the *Expositor* to the standards they set for themselves:

- Joseph Smith's public statements about his own marital status ("I can only find one" wife, May 26, 1844) are held against the revelation Hyrum read to the High Council in August 1843 authorizing plural marriage.
- The Nauvoo City Council's 1844 declaration of the *Expositor* as a "public nuisance" is evaluated against the law of the time — including by Dallin H. Oaks's own 1965 analysis.
- The Church's modern statements in the Gospel Topics essays are taken at face value, and measured against the contemporary denials of 1842–1844.

---

## What we document

We work with content that has been:

| Category | Description | Example from *Sudden Day* |
|---|---|---|
| **Contemporaneously sworn** | Statements made under oath at or near the time of the events described | Jane Law's affidavit on the penalty of damnation for refusing plural marriage (*Under Condemnation*) |
| **Contemporaneously denied** | Public denials that the Church now confirms were false | Joseph's May 26, 1844 "seven wives" sermon (*Seven Wives*) |
| **Subsequently acknowledged** | Claims the *Expositor* made that the Church itself has later admitted | Plural marriage practice, "carefully worded denials," Council of Fifty kingship vote |
| **Physically documented** | Events whose occurrence is not seriously in dispute | The destruction of the press, the Carthage killings |

---

## Anticipating apologetic responses

For every major claim, we document the standard apologetic response and explain why the source material holds up. Common defenses we address:

- *"The destruction was municipal-nuisance abatement, not a rights violation."* — Addressed on the source document page with Oaks's own concession.
- *"First Amendment framing is anachronistic."* — Addressed. The case still stands on state constitutional and common-law grounds, and more importantly, on the subsequent acknowledgments by the Church.
- *"The publishers were embittered apostates."* — Addressed. William Law was the Second Counselor in the First Presidency in January 1844. "Apostate" is a label applied after the fact; the factual claim is what matters.
- *"The tone was inflammatory, not journalistic."* — Addressed. Tone does not rebut evidence; the affidavits are either true or false on their own terms, and the 2014 Gospel Topics essay confirms the substance.
- *"Specific doctrinal charges (many gods) are unverified."* — Addressed. The King Follett Discourse was delivered publicly at general conference two months before the *Expositor*.

We steel-man these arguments — present them in their strongest form — before showing why the source material defeats them.

---

## Quality standards

### Every quote must have
- Exact text with original spelling/punctuation preserved
- Precise citation (*Expositor* Preamble, Resolution number, or named affidavit)
- Speaker identification
- Context notes

### Every track must have
- 100% source mapping (every lyric line traced)
- Historical context section
- At least one apologetic response addressed somewhere in the site (typically on the source document page)
- Accuracy verified against the *Expositor*'s full text

---

## What we avoid

**We do not:**
- Quote out of context in ways that change meaning
- Rely on 20th-century summaries when the 1844 text itself is accessible
- Exaggerate claims beyond what the text supports
- Ignore charitable interpretations without addressing them
- Combine quotes from different sections of the *Expositor* as if they were one statement

**We do:**
- Let the material speak for itself
- Build the strongest case from the single strongest source
- Document thoroughly
- Acknowledge where the Church itself now agrees

---

## Verification

All sources on this site are publicly accessible. We encourage readers to:

1. Read the full *Expositor* — not just our excerpts — at [FAIR Latter-day Saints' hosted full text](https://www.fairlatterdaysaints.org/answers/Primary_sources/Nauvoo_Expositor_Full_Text).
2. Check lyric-to-source mappings against the original.
3. Evaluate whether our characterizations are fair.
4. Point out any errors for correction via the project's [GitHub repository](https://github.com/imcmurray/Sudden-Day).

---

> *"The remedy can never be applied, unless the disease is known."* — *Nauvoo Expositor*, June 7, 1844
"""
    write(SITE / "methodology.md", content)


def build_terms() -> None:
    content = frontmatter({"title": "Terms of Use"}) + """\
## Purpose

*Sudden Day* is an educational and documentary project. Its purpose is to preserve and make accessible the contents of a specific 1844 primary source — the *Nauvoo Expositor* — together with original creative and analytical work that traces each claim on this site to that source.

---

## Public-domain source

The *Nauvoo Expositor* was published on June 7, 1844. Under United States copyright law, works published before 1928 are in the **public domain**. All quotations from the *Expositor* (including the affidavits, the "Citizens of Hancock County" letter, and the Preamble and Resolutions) are taken from public-domain materials.

---

## Fair use

Original commentary, analysis, and creative works on this site constitute fair use under 17 U.S.C. § 107. This includes:

- Commentary on and criticism of historical religious practices and teachings.
- Educational analysis with full source citations.
- Transformative creative works (lyrics and recordings) that comment on the underlying source material.

Every track on this site includes source documentation showing how lyrics trace to the *Nauvoo Expositor*.

---

## No affiliation

This project is **not affiliated with, endorsed by, or connected to** The Church of Jesus Christ of Latter-day Saints, Brigham Young University, FAIR Latter-day Saints, any ex-Mormon organization, or any related body. It is an independent historical-documentation project.

Links to FAIR Latter-day Saints and to Church of Jesus Christ materials are provided for source verification only and do not imply endorsement by or of those organizations.

---

## Accuracy commitment

- **Primary source first.** Every claim traces to the 1844 *Expositor* or to directly cited contemporaneous documents.
- **Full context.** We do not quote out of context in ways that change meaning.
- **Charitable reading.** We acknowledge reasonable interpretations before presenting our analysis — see the [source document page](/about/source/).
- **Complete citations.** Every lyric is mapped to its source on the track page.
- **Corrections welcome.** If we have made an error, we want to know. File an issue on the project's [GitHub repository](https://github.com/imcmurray/Sudden-Day).

---

## Content advisory

This project documents sworn testimony and contemporaneous reporting about coercion, deception, and the abuse of religious authority. The material includes specific accounts of adult women and teenage girls being pressured into plural marriage, of public denials that contradict now-acknowledged practice, and of extra-judicial violence. Readers are advised accordingly.

We present this material for historical documentation, not endorsement of any party.

---

## Disclaimer

The information on this website is provided for educational and informational purposes only. It is not intended as legal, religious, or professional advice.

Historical quotations reflect the views of their original authors, not the creators of this project. Our analysis represents our interpretation of the historical record.

---

## Contact

For corrections, questions, or concerns, please open an issue on the project's [GitHub repository](https://github.com/imcmurray/Sudden-Day).

---

*Last updated: April 2026.*
"""
    write(SITE / "terms.md", content)


def build_essays(tracks: dict[int, Track]) -> None:
    index = frontmatter({"title": "Essays"}) + """\
Long-form companion pieces to the album.
"""
    write(SITE / "essays" / "_index.md", index)

    essay_files = [
        ("intro-before-you-listen.md",     "Before You Listen",  "introduction"),
        ("album-analysis.md",              "Album Analysis",     "analysis"),
        ("epilogue-1890.md",               "1890",               "epilogue"),
        ("afterword-after-you-listen.md",  "After You Listen",   "afterword"),
        ("companion-essay.md",             "Companion Essay",    "companion"),
    ]
    for weight, (fname, title, kind) in enumerate(essay_files, start=1):
        src = ESSAYS / fname
        if not src.exists():
            # Leave a placeholder page for the companion essay until the user drops it in.
            if fname == "companion-essay.md":
                placeholder = frontmatter({
                    "title": title,
                    "draft": True,
                    "weight": weight,
                }) + """\
> **Placeholder.** The companion essay was attached to the source snippet as a personal-snippet file upload, which GitLab does not expose through the API or to personal access tokens. To publish this page:
>
> 1. Open the snippet in your browser.
> 2. Download `SUDDEN_DAY__A_Companion_Essay.md`.
> 3. Save it to `essays/companion-essay.md` in the repo.
> 4. Re-run `python3 scripts/build_hugo_content.py`.
"""
                write(SITE / "essays" / "companion-essay.md", placeholder)
            continue

        body = src.read_text()
        body = strip_source_footer(body)
        # Strip the essay's own top-level title since the frontmatter provides one.
        body = re.sub(r"^# [^\n]*\n(?:## [^\n]*\n)?(?:### [^\n]*\n)?\n*---\n+", "", body, count=1)
        essay_slug = fname.removesuffix(".md")
        uuid = SUNO_UUIDS_ESSAY.get(essay_slug)
        fm_fields: dict = {
            "title": title,
            "weight": weight,
            "tags": [kind],
        }
        if uuid:
            fm_fields["suno_url"] = suno_url(uuid)
        fm = frontmatter(fm_fields)
        prefix = "{{< suno >}}\n\n" if uuid else ""
        write(SITE / "essays" / fname, fm + prefix + body)


def main() -> None:
    tracks: dict[int, Track] = {}
    for p in sorted(ESSAYS.glob("track-*.md")):
        t = parse_track(p)
        tracks[t.number] = t
    print(f"Parsed {len(tracks)} tracks")
    build_home()
    build_about()
    build_mission()
    build_faq()
    build_methodology()
    build_terms()
    build_tracks_index()
    build_acts_index()
    build_act_pages(tracks)
    build_track_pages(tracks)
    build_essays(tracks)
    print("done.")


if __name__ == "__main__":
    main()
