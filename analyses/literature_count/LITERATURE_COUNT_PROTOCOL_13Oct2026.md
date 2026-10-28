# Structured literature count: protocol (fixed 13 Oct 2026)

- **Status: FIXED on 13 Oct 2026, before any record was screened.** Drafted the same day and approved by the user
  (choices L-1 to L-4, section 8). Its SHA-256 is recorded in `Implementation/revision_1/literature_count/PROTOCOL_SHA256.txt`
  before the searches run. Nothing in it changes after that. Any later change is dated and reported as a deviation.
- **Why.** Strategy step 2 and decision N-2 (a). Suggestion 1 in `PAPER_STRENGTHENING_SUGGESTIONS_13Oct2026.md`. The
  user chose on 13 Oct 2026 to run the baselines and this count before writing the manuscript.
- **What the count may support.** A statement about published practice in decomposition-based air-quality forecasting
  (for example "k of n coded studies decompose the whole series before splitting it"). Not a "first" claim, and not a
  systematic review (no PRISMA claim beyond the flow counts).

## 1. Question

Among peer-reviewed studies that forecast air quality with a hybrid of signal decomposition and a statistical or
machine-learning model:
1. **Timing.** How often is the target series decomposed in a way that lets data after the forecast origin enter the
   inputs?
2. **Baselines.** How often is a non-decomposed version of the same model reported, and how often persistence?
3. **Interpretation.** How often are modes, or attributions to them, read as physical drivers, timescales or guidance
   for interventions?

## 2. Sources and search

- **Sources: OpenAlex and Scopus.**
  - OpenAlex: a reproducible Boolean query with open-access status, no key needed.
  - Scopus Search API (a curated index), through the authors' Elsevier API key. The entitlement check of 13 Oct 2026
    passed (`lc_search.py check`).
  - The key stays in a local file and never enters the repository or any output.
- **Not used:**
  - ScienceDirect Search API: the key is not authorised for it (HTTP 401 on 13 Oct 2026). Scopus indexes the same
    Elsevier journals, so no record is lost for identification.
  - Web of Science: no key.
  - Semantic Scholar and Crossref: their search here has no Boolean support, so a reproducible query is not
    possible. Dropped from the draft.
- **Exact strings per source:** in `Implementation/revision_1/literature_count/lc_search.py` (`QUERIES`). Scopus uses
  `TITLE-ABS-KEY`, which also searches author keywords, and `forecast*`/`predict*` truncation. The run saves the raw
  exports, the date and the hashes in `search_log.json`.
- **Not used:** Sci-Hub or any other unlicensed copy.
- **Query** (title and abstract, OpenAlex `title_and_abstract.search`):

  `("empirical mode decomposition" OR CEEMDAN OR EEMD OR "variational mode decomposition" OR VMD OR wavelet OR
  "singular spectrum analysis") AND ("air quality" OR AQI OR "PM2.5" OR PM10 OR "particulate matter" OR NO2 OR ozone)
  AND (forecast OR forecasting OR prediction)`
- **Filters:** journal articles and conference papers, years per L-2.
- **Size check (13 Oct 2026, hit counts only, no record read):** OpenAlex 370 records. Scopus 520 (`TITLE-ABS-KEY`).
- **Abstracts for screening.** From OpenAlex where available, otherwise the Scopus abstract, otherwise the
  publisher's landing page.
- **Logging.** The search date, the exact query strings and the raw exports (with DOIs) are saved. Duplicates are
  removed by DOI, then by normalised title.

## 3. Eligibility (title and abstract, then full text)

**Include:**
- an air-quality variable is forecast out of sample (AQI, PM2.5, PM10, NO2, O3, SO2, CO, or a composite);
- the target series, or the series of a predictor, is decomposed (EMD family, VMD, wavelet, SSA or similar), and the
  components enter a forecasting model;
- the paper reports forecast evaluation on held-out data;
- English, peer reviewed.

**Exclude:** reviews and surveys; decomposition used only for description; spatial interpolation without a time
forecast; retracted papers. Uncertain records go to the full-text stage. Every exclusion has one recorded reason.

## 4. Coding items (full text; definitions fixed here)

| Item | Values |
|---|---|
| T1 Target | AQI, PM2.5, PM10, NO2, O3, other |
| T2 Decomposition method | EMD, EEMD, CEEMDAN, ICEEMDAN, VMD, wavelet, SSA, other (several allowed) |
| T3 **Decomposition timing** | (i) the whole series decomposed once, then split. (ii) Training and test decomposed separately, each as a block (the test block still uses later test data). (iii) Causal: at each forecast origin from past data only (rolling or expanding window, or a causal transform). (iv) Other, described. (v) Not stated or unclear |
| T4 Boundary at the forecast origin | Handling stated (yes, no) |
| T5 Non-decomposed version of the same model reported | Yes, no |
| T6 Persistence (or naive) baseline reported | Yes, no |
| T7 Reported gain from decomposition | Relative RMSE (or MAE) reduction against T5, as reported, else not reported |
| T8 **Interpretation** | Modes or attributions read as physical drivers, timescales or intervention guidance: yes (with a short quote and page), no |
| T9 Explanation method | SHAP, attention, permutation, other, none |
| T10 Code or data available | Yes, no |
| T11 Full-text source | URL used for coding |

- **Leakage-prone** = T3 (i) or (ii). **Causal** = T3 (iii). "Not stated" (v) is reported as its own category, never
  merged into either.
- A paper with several experiments is coded on its main reported model.
- **T3 decision rules.**
  - Decomposition of the full series, then building the windows and splitting: (i).
  - A discrete wavelet transform or any non-causal filter over the full series: (i).
  - The test period decomposed once as a block, separately from training: (ii).
  - Each forecast origin decomposed from data up to that origin only (rolling or expanding), or a transform stated to
    be causal at each origin: (iii).
  - Timing inferred from a figure or flowchart is coded only if unambiguous. Otherwise (v).
- **T8 decision rule.** Yes when the paper links a mode, a component or its importance to a named physical process
  or source (for example "IMF3 reflects weekly traffic"), or derives timing or policy recommendations from modes.
  Describing modes only as high or low frequency, or as noise and trend, is No.

## 5. Coding sample

- **Accessible full text:** an open copy listed by OpenAlex (any open-access location, including an accepted manuscript
  or preprint) that opens without a login. A preprint is coded as the preprint and flagged.
- **Sample (L-3):** if more than 80 included records have an accessible full text, 60 are drawn without replacement
  with `numpy.random.default_rng(20261013)` from the list sorted by DOI. Otherwise all are coded.
- Records without an accessible full text are counted and described (year, venue), not coded.

## 6. Reliability

Per L-4. The first author codes 20% of the coded sample (at least 12), drawn with `numpy.random.default_rng(20261014)`,
blind to the first coding. Agreement on T3 and T8 is reported (percentage
and Cohen's κ). Disagreements are resolved by discussion and the resolution is logged.

## 6a. Who screens and codes

- Title and abstract screening and the first full-text coding are done with AI assistance (Claude, Anthropic) under
  these rules. Every decision is logged with its reason and the evidence (quote, page or section).
- The human check is the first author's blind second coding (section 6). Exclusions at the title and abstract stage
  are not double-screened, which is stated as a limit.

## 7. Outputs and reporting

- Screening log (every record and its decision), coding sheet (CSV), and flow counts (identified, duplicates, screened,
  excluded with reasons, full text sought and obtained, coded).
- For T3, T5, T6 and T8: counts and shares with Wilson 95% intervals, over the coded sample.
- Secondary: the T3 shares for papers published 2015-2020 and 2021-2025.
- All in the SI, with the query strings and dates.
- **Limits stated in the paper:**
  - OpenAlex and Scopus coverage;
  - open-access full texts only (publication-access bias);
  - AI-assisted screening and first coding, with a human check on coding only;
  - English only.

## 8. Choices to make before the protocol is fixed

| ID | Question | Options | Recommended |
|---|---|---|---|
| L-1 | Sources | (a) OpenAlex, with Semantic Scholar and Crossref as cross-checks (all available here). (b) As (a), plus Scopus and Web of Science exports that the authors run through their university library with the query above (CSV of DOIs). (c) As (a), plus Scopus and ScienceDirect through the authors' Elsevier API key (added 13 Oct 2026, the user has a key) | (c), with Scopus if the key is entitled for it. Reviewers expect at least one curated index. Web of Science can be added under (b) later if wanted |
| L-2 | Years | (a) 2015-2025. (b) 2018 to the search date | (a). It covers the period of the hybrid models and gives complete years |
| L-3 | Coding sample | (a) All included records with an open full text. (b) A seeded random sample of 60 of them. (c) As (a), plus abstract-only coding of paywalled papers on T5, T6 and T8 | (b) if more than about 80 are included, otherwise (a). 60 gives a 95% interval of about ±13 points on a share near 50% |
| L-4 | Second coder | (a) The first author codes a blind random 20% (at least 12 papers). (b) A co-author does. (c) None | (a) or (b). Without it the count is weaker, and strategy option (a) assumes it |

**A point for the authors.** Nature Portfolio asks authors to document the use of large language models in the
Methods. If screening or coding is AI-assisted, the authors decide how to state that. The human second-coder check
(L-4) also helps here.

**Decided by the user, 13 Oct 2026:**
- L-1: (c). The user has an Elsevier API key. The check passed for Scopus and failed for ScienceDirect (HTTP 401),
  so the sources are OpenAlex and Scopus (section 2).
- L-2: (a), 2015-2025.
- L-3: (b) if more than about 80 records are included after screening, otherwise (a). Seed fixed at 20261013.
- L-4: (a). The first author codes a blind random 20% (at least 12 papers).

## 9. Effort (estimate)

- Search and deduplication: hours.
- Screening about 600 titles and abstracts after deduplication (OpenAlex 370, Scopus 520, overlapping): about a day.
- Full-text coding of up to 60 papers: several days.
- Second coder: about a day.
