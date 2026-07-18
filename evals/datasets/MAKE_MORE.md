# Adding cases to the golden dataset

The dataset lives in `golden_v1.jsonl` (ground truth) with a matching recorded-LLM fixture in
`../fixtures/llm/<id>.json`. **Don't hand-edit those files** — author cases in `build_golden.py`
and regenerate. The builder asserts every quoted span is a literal substring of the resume, which
is the exact check the pipeline applies; a typo fails loudly at build time instead of silently
skewing a benchmark later.

## Steps

1. Open `build_golden.py` and copy an existing `add_case(...)` block.
2. Give it a unique `id` and a `kind` of `real`, `planted_lie`, or `edge` (only affects reporting
   buckets).
3. Write the `resume_text` and `jd_text`.
4. For each claim, call `claim(...)`:
   - `text` — the human-readable claim (this is the ground-truth key).
   - `category` — one of `skill | employment | education | project | credential`.
   - `quote` — wrap it in `_quote(_r, "...")`; it MUST be a verbatim substring of the resume, or the
     build fails.
   - `is_verified` / `is_fabricated` / `evidence_type` — the human judgement.
   - `normalized_skill` — lowercase canonical form for skill claims (aids matching).
   - `asserted_*` — for employment claims fill `asserted_start` / `asserted_end` ("YYYY-MM"); for
     skill-years claims fill `asserted_years`. The consistency checker uses these.
   - `model_extracts=False` — use this to model a claim the LLM *missed* (a recall/false-negative case).
5. Optional `model_noise=[...]` — spurious claims the model invented. If the `quote` is real resume
   text, it becomes a precision false-positive; if the `quote` is NOT in the resume, the citation
   guardrail must discard it (tests the guardrail).
6. Optional `evidence=[evidence(...)]` — recorded connector evidence (e.g. a GitHub match) that
   should verify a claim. `claim_key` attaches it to a claim by normalized skill or text.
7. Regenerate and re-run:

   ```bash
   make eval-build     # rewrites golden_v1.jsonl + fixtures (asserts all quotes)
   make eval-report    # recomputes the numbers
   make eval-test      # sanity-check the harness still passes
   ```

## Guidelines for good cases

- **Planted lies should be catchable in principle** — a fabricated employer (no evidence → stays
  unverified), impossible tenure (consistency `date_overlap`), inflated years
  (`years_exceed_career_span`), or false ownership (no corroborating artifact). Mark them
  `is_fabricated=True, is_verified=False`.
- **Edge cases should be legitimately hard, not lies** — career gaps, non-ASCII names, firewall-only
  work with no public footprint. These must stay `is_fabricated=False`; the correct outcome is
  "unverified", never "contradicted".
- **Keep imperfections realistic.** A dataset where the model scores a flat 100% proves nothing —
  bake in the occasional miss or spurious extraction so the metrics have signal.

## Recording fixtures against a live model (paid — ask first)

The default fixtures are authored offline. To measure the *live* model instead, run each case's
resume through the real extractor, save the returned `ExtractedClaims` JSON into the fixture's
`extracted_claims`, set the report's `provider` to the model id, and re-run. This costs money and
hits a paid API — get sign-off before doing it in bulk.
