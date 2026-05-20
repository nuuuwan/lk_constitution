# Data Format — Constitution of Sri Lanka (JSON)

Source: *The Constitution of the Democratic Socialist Republic of Sri Lanka*
(As amended up to 31 October 2022, Revised Edition 2023, including the Twenty-First Amendment)

---

## Top-level document

```json
{
  "title": "The Constitution of the Democratic Socialist Republic of Sri Lanka",
  "edition": "Revised Edition – 2023",
  "amended_up_to": "2022-10-31",
  "last_amendment": "Twenty-First Amendment",
  "published_by": "Parliament Secretariat",
  "preamble": "<full text of the Preamble / SVASTI>",
  "chapters": [ /* Chapter objects — see below */ ],
  "schedules": [ /* Schedule objects — see below */ ]
}
```

---

## Chapter object

```json
{
  "number": "I",
  "title": "The People, the State and Sovereignty",
  "articles": [ /* Article objects — see below */ ]
}
```

`number` uses Roman numerals as printed (e.g. `"I"`, `"VIIA"`, `"XIX B"`).

---

## Article object

```json
{
  "number": "4",
  "title": "Exercise of Sovereignty",
  "text": "The Sovereignty of the People shall be exercised and enjoyed in the following manner:–",
  "clauses": [ /* Clause objects — see below */ ],
  "footnotes": [ /* Footnote objects — see below */ ],
  "repealed": false
}
```

| Field | Type | Notes |
|---|---|---|
| `number` | string | Article number as printed; may include a letter suffix, e.g. `"14A"`, `"41B"`, `"104GG"` |
| `title` | string | Marginal heading appearing beside the article text; `null` when absent |
| `text` | string | Introductory text of the article before any numbered/lettered clauses; may be the full article text when there are no sub-clauses |
| `clauses` | array | Top-level numbered clauses `(1)`, `(2)`, …; empty array when the article has no sub-clauses |
| `footnotes` | array | Amendment footnotes that appear below the article |
| `repealed` | boolean | `true` when the article heading reads "Repealed" |

---

## Clause object

Clauses may be nested up to three levels:

```
Article
  └─ Clause         (1), (2), (3), …          numeric
       └─ Sub-clause (a), (b), (c), …          alphabetic
            └─ Sub-sub-clause  (i), (ii), …    Roman numeral
```

```json
{
  "label": "(1)",
  "text": "No citizen shall be discriminated against on the grounds of race ...",
  "sub_clauses": [
    {
      "label": "(a)",
      "text": "the legislative power of the People shall be exercised by Parliament ...",
      "sub_clauses": [
        {
          "label": "(i)",
          "text": "the freedom to return to Sri Lanka.",
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
| `text` | string | Full text of this clause (excluding the text of any sub-clauses) |
| `sub_clauses` | array | Next-level clauses; empty array at the leaf level |

---

## Footnote object

```json
{
  "marker": "184",
  "text": "Inserted by the Seventh Amendment to the Constitution Sec. 5(b)."
}
```

Footnote markers appear as superscript numbers in the printed text and as numeric strings in this schema.

---

## Schedule object

```json
{
  "number": 1,
  "title": "First Schedule",
  "referred_by_article": "5",
  "description": "Names of Administrative Districts",
  "content_type": "list",
  "items": [
    { "number": 1, "value": "Colombo" },
    { "number": 2, "value": "Gampaha" }
  ]
}
```

`content_type` is one of:

| Value | Used for |
|---|---|
| `"list"` | Enumerated items (Schedules 1, 5, 6) |
| `"image"` | The National Flag (Schedule 2) |
| `"text_and_image"` | The National Anthem words + music (Schedule 3) |
| `"oath"` | Oath / affirmation text (Schedule 4) |
| `"legislative_list"` | Ninth Schedule Provincial / Reserved / Concurrent lists |
| `"text"` | Any other schedule with free-form text |

For `"legislative_list"` schedules (Ninth Schedule), an additional `"lists"` field replaces `"items"`:

```json
{
  "number": 9,
  "title": "Ninth Schedule",
  "referred_by_article": null,
  "content_type": "legislative_list",
  "lists": [
    {
      "list_id": "I",
      "name": "Provincial Council List",
      "items": [
        { "number": 1, "subject": "Law and order", "description": "..." }
      ]
    },
    {
      "list_id": "II",
      "name": "Reserved List",
      "items": [ /* … */ ]
    },
    {
      "list_id": "III",
      "name": "Concurrent List",
      "items": [ /* … */ ]
    }
  ]
}
```

---

## Complete structural example

```json
{
  "title": "The Constitution of the Democratic Socialist Republic of Sri Lanka",
  "edition": "Revised Edition – 2023",
  "amended_up_to": "2022-10-31",
  "last_amendment": "Twenty-First Amendment",
  "published_by": "Parliament Secretariat",
  "preamble": "The PEOPLE OF SRI LANKA having, by their Mandate freely expressed ...",
  "chapters": [
    {
      "number": "I",
      "title": "The People, the State and Sovereignty",
      "articles": [
        {
          "number": "1",
          "title": "The State",
          "text": "Sri Lanka (Ceylon) is a Free, Sovereign, Independent and Democratic Socialist Republic and shall be known as the Democratic Socialist Republic of Sri Lanka.",
          "clauses": [],
          "footnotes": [],
          "repealed": false
        },
        {
          "number": "4",
          "title": "Exercise of Sovereignty",
          "text": "The Sovereignty of the People shall be exercised and enjoyed in the following manner:–",
          "clauses": [
            {
              "label": "(a)",
              "text": "the legislative power of the People shall be exercised by Parliament, consisting of elected representatives of the People and by the People at a Referendum;",
              "sub_clauses": []
            },
            {
              "label": "(b)",
              "text": "the executive power of the People, including the defence of Sri Lanka, shall be exercised by the President of the Republic elected by the People;",
              "sub_clauses": []
            }
          ],
          "footnotes": [],
          "repealed": false
        }
      ]
    },
    {
      "number": "VIIA",
      "title": "The Constitutional Council",
      "articles": [
        {
          "number": "41A",
          "title": "Constitution of the Constitutional Council",
          "text": "There shall be a Constitutional Council ...",
          "clauses": [
            {
              "label": "(1)",
              "text": "The Constitutional Council shall consist of the following members:–",
              "sub_clauses": [
                {
                  "label": "(i)",
                  "text": "one Member of Parliament nominated by the Party ...",
                  "sub_clauses": []
                }
              ]
            }
          ],
          "footnotes": [
            {
              "marker": "23",
              "text": "Substituted by the Nineteenth Amendment to the Constitution Sec. 3."
            }
          ],
          "repealed": false
        },
        {
          "number": "33A",
          "title": "Repealed",
          "text": null,
          "clauses": [],
          "footnotes": [],
          "repealed": true
        }
      ]
    }
  ],
  "schedules": [
    {
      "number": 1,
      "title": "First Schedule",
      "referred_by_article": "5",
      "description": "Names of Administrative Districts",
      "content_type": "list",
      "items": [
        { "number": 1, "value": "Colombo" },
        { "number": 2, "value": "Gampaha" }
      ]
    },
    {
      "number": 9,
      "title": "Ninth Schedule",
      "referred_by_article": null,
      "content_type": "legislative_list",
      "lists": [
        {
          "list_id": "I",
          "name": "Provincial Council List",
          "items": [
            { "number": 1, "subject": "Law and order", "description": "..." }
          ]
        }
      ]
    }
  ]
}
```

---

## Hierarchy summary

```
constitution
├── preamble                (string)
├── chapters[]
│   └── articles[]
│       ├── clauses[]
│       │   └── sub_clauses[]        (alpha labels)
│       │       └── sub_clauses[]    (Roman numeral labels)
│       └── footnotes[]
└── schedules[]
    ├── items[]              (for list / text schedules)
    └── lists[].items[]      (for legislative_list schedules)
```

---

## Notes on numbering conventions

- **Article numbers** with letter suffixes (`14A`, `41B`, `104GG`, `155FF`, `155FFF`) represent articles inserted by later amendments and are stored as strings.
- **Chapter numbers** with letter suffixes (`VIIA`, `XIVA`, `XVIIA`, `XVIIIA`, `XIXA`, `XIXB`) indicate chapters added by amendment.
- **Footnote markers** are integers encoded as strings (matching the superscripts in the printed text).
- The `repealed` flag is set for articles explicitly listed as "Repealed" (e.g. Articles 33A, 96A) so they are preserved in the dataset with their position intact.
