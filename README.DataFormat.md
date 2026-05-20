# Data Format — Constitution of Sri Lanka (JSON)

Source: *The Constitution of the Democratic Socialist Republic of Sri Lanka*

---

## Folder structure

Each version of the constitution is stored in a self-contained folder under `data/parsed/`:

```
data/parsed/
└── lk-constitution-<date-last-updated>/
    ├── top-level.json
    ├── preamble.json
    ├── chapter-<NUMBER>.json   (one per chapter)
    └── schedule-<NUMBER>.json  (one per schedule)
```

`<date-last-updated>` is the ISO 8601 date of the most recent amendment included in that version.

---

## `top-level.json`

Metadata and an index of all chapters and schedules. Does **not** embed full content — it references the individual files by name.

```json
{
  "title": "<document title>",
  "edition": "<edition string>",
  "amended_up_to": "<YYYY-MM-DD>",
  "last_amendment": "<amendment name>",
  "published_by": "<publisher>",
  "chapters": [
    { "number": "<roman numeral>", "title": "<chapter title>", "file": "chapter-<NUMBER>.json" }
  ],
  "schedules": [
    { "number": "<integer>", "title": "<schedule title>", "file": "schedule-<NUMBER>.json" }
  ]
}
```

---

## `preamble.json`

```json
{
  "text": "<full preamble text>"
}
```

---

## Chapter file — `chapter-<NUMBER>.json`

`<NUMBER>` is the Roman numeral of the chapter as printed. Chapter numbers added by amendment may include a letter suffix (e.g. `VIIA`, `XIXB`).

```json
{
  "number": "<roman numeral>",
  "title": "<chapter title>",
  "articles": [ /* Article objects — see below */ ]
}
```

---

## Article object

```json
{
  "number": "<article number>",
  "title": "<marginal heading>",
  "text": "<introductory text, or full text if no sub-clauses>",
  "clauses": [ /* Clause objects — see below */ ],
  "footnotes": [ /* Footnote objects — see below */ ],
  "repealed": false
}
```

| Field | Type | Notes |
|---|---|---|
| `number` | string | Article number as printed; may include a letter suffix (e.g. `"14A"`, `"104GG"`) |
| `title` | string | Marginal heading beside the article text; `null` when absent |
| `text` | string | Introductory text before any sub-clauses; may be the full article text when `clauses` is empty |
| `clauses` | array | Top-level clauses; empty array when the article has no sub-clauses |
| `footnotes` | array | Amendment footnotes appearing below the article |
| `repealed` | boolean | `true` when the article has been repealed |

---

## Clause object

Clauses may be nested up to three levels:

```
Article
  └─ Clause            (1), (2), (3), …     numeric
       └─ Sub-clause   (a), (b), (c), …     alphabetic
            └─ Sub-sub-clause (i), (ii), …  Roman numeral
```

```json
{
  "label": "(1)",
  "text": "<clause text>",
  "sub_clauses": [
    {
      "label": "(a)",
      "text": "<sub-clause text>",
      "sub_clauses": [
        {
          "label": "(i)",
          "text": "<sub-sub-clause text>",
          "sub_clauses": []
        }
      ]
    }
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `label` | string | The printed label including parentheses, e.g. `"(1)"`, `"(a)"`, `"(i)"` |
| `text` | string | Text of this clause, excluding the text of any sub-clauses |
| `sub_clauses` | array | Next-level clauses; empty array at the leaf level |

---

## Footnote object

```json
{
  "marker": "<superscript number>",
  "text": "<amendment description>"
}
```

`marker` is the superscript number from the printed text, stored as a string.

---

## Schedule file — `schedule-<NUMBER>.json`

`<NUMBER>` is the ordinal integer of the schedule.

```json
{
  "number": "<integer>",
  "title": "<schedule title>",
  "referred_by_article": "<article number or null>",
  "description": "<short description>",
  "content_type": "<content type>",
  "items": [ /* for list / text schedules */ ]
}
```

`content_type` is one of:

| Value | Used for |
|---|---|
| `"list"` | An enumerated list of items |
| `"image"` | A graphical element |
| `"text_and_image"` | Combined text and graphical content |
| `"oath"` | An oath or affirmation text |
| `"legislative_list"` | A schedule containing multiple named sub-lists |
| `"text"` | Any other free-form text schedule |

For `"list"` schedules, `items` is an array of:

```json
{ "number": "<integer>", "value": "<item text>" }
```

For `"oath"` schedules, `items` is replaced by:

```json
{ "text": "<oath text>" }
```

For `"legislative_list"` schedules, `items` is replaced by a `lists` array:

```json
{
  "number": "<integer>",
  "title": "<schedule title>",
  "referred_by_article": "<article number or null>",
  "content_type": "legislative_list",
  "lists": [
    {
      "list_id": "<identifier>",
      "name": "<list name>",
      "items": [
        { "number": "<integer>", "subject": "<subject>", "description": "<text>" }
      ]
    }
  ]
}
```

---

## Hierarchy summary

```
lk-constitution-<date>/
├── top-level.json            edition metadata + index of all files
├── preamble.json             full preamble text
├── chapter-<NUMBER>.json     one per chapter
│   └── articles[]
│       ├── clauses[]
│       │   └── sub_clauses[]          (alpha labels)
│       │       └── sub_clauses[]      (Roman numeral labels)
│       └── footnotes[]
└── schedule-<NUMBER>.json    one per schedule
    ├── items[]               (list / oath / text schedules)
    └── lists[].items[]       (legislative_list schedules)
```

---

## Notes on numbering conventions

- **Article numbers** may include a letter suffix to represent articles inserted by later amendments.
- **Chapter numbers** use Roman numerals and may include a letter suffix for chapters added by amendment.
- **Footnote markers** are integers encoded as strings, matching the superscripts in the printed text.
- The `repealed` flag preserves repealed articles in the dataset with their position intact rather than omitting them.
