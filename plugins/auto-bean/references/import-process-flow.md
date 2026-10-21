# Import process flow

This diagram summarizes [auto-bean-import](../skills/auto-bean-import/SKILL.md). Orange nodes show human involvement; dotted branches are conditional clarification loops.

- **∥** marks processing or categorization that may use parallel statement-scoped workers.
- **◆** marks potential coordination bottlenecks owned by the main import agent, rather than measured runtime delays.

Each statement resumes from its persisted status and advances when ready. Independent safe work continues while questions are pending; unresolved cross-statement transfer or duplicate evidence holds the affected posting cohort. All ledger writes, including accounts, documents, and prices, remain serialized. Import alone updates shared status and brokers worker questions.

```mermaid
flowchart TD
    S([Start or resume import]) --> D["Discover sources<br/>Read status and fingerprints"]
    D --> E{"Already done?"}
    E -- Yes --> R{"Explicit rework requested?"}
    R -- No --> SK([Skip statement])
    R -- Yes --> P
    E -- No --> P["∥ Process source<br/>Extract and validate evidence"]

    P --> A["◆ Inspect accounts<br/>Plan openings and document references"]
    A --> B["Validate approved structure edits<br/>Check opening balances"]
    B --> C["∥ Categorize transactions"]
    C --> X["◆ Review batch transfers and duplicates<br/>Assign dispositions and one transfer owner"]
    X --> W["Write transaction candidate serially<br/>Validate ledger"]
    W --> F["◆ Final review<br/>Check closing balances and exact candidate"]

    P <-.-> HP["Human: source clarification<br/>or manual resolution"]
    A <-.-> HA["Human: resolve account/date questions<br/>Approve new account structure"]
    B <-.-> HB["Human: choose balance remediation"]
    C <-.-> HC["Human: resolve category<br/>or transaction ambiguity"]
    X <-.-> HX["Human: resolve uncertain<br/>transfer or duplicate decisions"]
    W <-.-> HW["Human: resolve missing facts<br/>or repair needing direction"]

    F --> AP{"Human approves<br/>exact validated result?"}
    AP -- "No or pending" --> H["Keep review or blocked state<br/>Apply recovery rules if rejected"]
    H -- "Correct and revalidate" --> F
    AP -- Yes --> DN["Mark statement done"]

    DN --> PR["After statement writes/reviews:<br/>Run or resume price epilogue"]
    PR --> PC{"Price edits?"}
    PC -- Yes --> PA["Human: separately approve<br/>validated price candidate"]
    PC -- No --> M["Consolidate eligible memory suggestions"]
    PA -- Approved --> M
    PA -- Pending --> PP["Keep price follow-up pending<br/>Statements remain done"]
    PP --> M
    M --> END([Summarize outcomes and remaining actions])

    classDef human fill:#fff1d6,stroke:#b7791f,color:#222;
    class HP,HA,HB,HC,HX,HW,AP,PA human;
```

Transaction candidates are written and validated before final statement approval. Acceptance requires explicit approval of the exact candidate after its hashes and validation are rechecked. Rejected candidates follow the recovery rules and return to the owning blocked stage; the correction arrow summarizes that recovery, which may revisit an earlier stage.

The price epilogue runs once after statement writes and current review decisions, including when some statements remain pending. It skips fetching only when there are no new writes and no pending price follow-ups. A statement can remain `done` while price approval is pending; the overall import is `Complete` only when all in-scope statements are `done` and no follow-up or price approval remains.

For detailed transitions and recovery, see [status handling](import-status-reading.md), [workflow rules](workflow-rules.md), and [candidate review](candidate-review.md).
