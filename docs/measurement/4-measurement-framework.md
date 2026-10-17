# Measurement framework: how we will know whether the change moved the assistants

**Decision this serves:** whether the one change applied to launchyourfirstwebsite.com moved how ChatGPT, Gemini and Claude surface it, on which rung of the ladder, relative to the untreated control site levelupsql.com, by more than the smallest effect worth claiming.

> **Status:** written on 2026-10-17 for issue #4, attempt 1, from the merged research `docs/research/3-assistant-citation.md` (#3) and the owner's decisions on #1 and #2 (treated and control sites confirmed; network-bound steps run in GitHub Actions, standing rule O6). This is a contract, not an implementation: #5 builds the scorer, the collector and the recording template against it. Nothing here has been collected. Section 16 says what has to exist before any number can be read.
>
> Every claim below that rests on an assumption carries **[assumed]**. Everything taken from #3 carries #3's own grade where it matters.

## 1. In five lines

1. One site is treated, one is the control. The unit an arm is assigned to is a **site**; the unit a result is counted in is a **response** - one question, one assistant, one surface, one repeat.
2. The outcome is a ladder, not "cited". *Indexed* is a per-domain, per-engine state the owner reads off a console. *Searched* and *retrieved* are per-response levels that only two API surfaces can see. *Named*, *linked*, *cited* and *paraphrased without attribution* are per-response surfaced levels scored by a mechanical rule.
3. Every per-response metric is a numerator over the count of collected responses in one cell (site, assistant, surface, arm). Cells are never pooled across surfaces or assistants.
4. The primary metric is the **retrieved rate** on the Gemini and Claude API surfaces, because #3 expects it to move and it is observable there. Everything above it is reported per rung; the smallest effect worth claiming on any per-response rung is 10 percentage points, spread over at least two questions, with the control not moving by as much.
5. The store is this repository: one JSON file per response, one JSON file per indexing report, under `data/`. The question set, the fingerprints, the settings and the arm dates are frozen before the baseline and the scorer refuses records that disagree with them.

## 2. The two units

- **Assigned:** a site. launchyourfirstwebsite.com is the treated site; levelupsql.com is the control. The assignment is fixed by design (#3, confirmed by the owner on #1, 2026-10-17) and cannot flip during the experiment. There is no third arm: a question not tagged to one of the two sites does not exist in this framework.
- **Counted:** a response. One question, asked once, in a fresh conversation, to one assistant, on one surface, in one arm. Five repeats of one question are five responses and are counted as five, deliberately, because repeat-to-repeat variation in whether the assistant searches is the quantity the design rests on; they are never counted as five *people* or five *sites*. The question is the stratum, not the unit.

"Exposure" in the analyst's sense is collection: a response counts once it is collected, whether or not it mentions any site. A response that could not be collected is recorded with a status saying why and is excluded from the denominator, never silently dropped and never scored as zero.

## 3. The ladder

Each rung has its own heading, its own observation rule per surface, and its own way of saying "cannot be observed here". A rung a surface cannot observe is recorded as `"unobservable"` on that surface, never as `false` and never as zero. The order from the bottom:

| Rung | Unit | Where it is read | Who records it |
|---|---|---|---|
| Indexed | per domain, per engine, per date | Google Search Console, Bing Webmaster Tools | the owner, by hand |
| Searched | per response | API response body; visible indicator in an app | collector |
| Retrieved | per response | API response body only (Claude, Gemini) | collector |
| Named, Linked, Cited, Paraphrased without attribution | per response | response text and the response's citations or visible sources | scorer, from the stored record |

### 3.1 Indexed

**Definition.** A domain is *indexed* in an engine on a date if the engine's own console reports at least one page of that domain as indexed on that date. It is a state with three values: `indexed`, `not-indexed`, `not-recorded`.

**Where it comes from.** Only the owner's console reports: Google Search Console for Google, Bing Webmaster Tools for Bing. It is not derived from responses and it is not fetched - an Actions run can reach the sites (O6), but fetching a page says nothing about whether an engine has indexed it (#3, "How to settle both in minutes"). Brave has no console (#3), so the *indexed* rung has two engines, and Brave's index is observed only indirectly, through Claude's *retrieved* rung.

**How it is read.** `indexed` when `homepage_indexed` is `true` or `indexed_pages` is at least 1 in the report; `not-indexed` when the report says the property is verified and both say otherwise; `not-recorded` when no report exists for that domain, engine and arm. The scorer prints `not-recorded` and never substitutes `not-indexed` for it. Section 11.5 gives the report file.

**Which report belongs to which arm.** The baseline state is the most recent report dated on or before `change_applied_on` in `data/arms.json`; the post-change state is the most recent report dated at least 14 days after it (#3, "When to measure: indexing").

### 3.2 Searched

**Definition.** The assistant issued at least one web search while producing this response.

**Per surface:**

| Surface | Observable | Read from |
|---|---|---|
| Claude API | yes | any content block with `type: "server_tool_use"` and `name: "web_search"` in the response; equivalently any `web_search_tool_result` block |
| Gemini API | yes | `candidates[0].groundingMetadata.webSearchQueries` present and non-empty |
| OpenAI API | **unknown** - #3 could not reach OpenAI's documentation | recorded `"unobservable"` until the driver confirms, from the documentation, which output item records a search; the raw response is stored verbatim so it can be re-scored then (section 16) |
| Any consumer app (ChatGPT, Gemini app, Claude.ai) | weakly - as *visibly searched* | the collector records whether the app showed a searching indicator or a sources panel during the reply; stored in the same `searched` field with `searched_evidence: "visible-indicator"` so the two readings are never confused |

**Why it is on the ladder at all.** It is the rung below *retrieved* and the quantity the treated-site choice rests on (#3: "An assistant only cites a page when it decides to search"). It is also the guardrail: the change to the site should not move how often an assistant searches for a question, so a searched rate that moves between arms is a sign the model or the trigger changed, not the site (section 10).

### 3.3 Retrieved

**Definition.** The site appears in the set of results the assistant saw while producing this response, whether or not it went on to use it.

**Per surface:**

| Surface | Observable | Read from | Match rule |
|---|---|---|---|
| Claude API | yes [verified by #3] | every `web_search_tool_result` block's `content[]` items of `type: "web_search_result"`, field `url` | the URL's host equals the domain or ends in `.` + the domain |
| Gemini API | yes [verified-excerpt in #3] | `candidates[0].groundingMetadata.groundingChunks[].web.uri` and `.web.title` | the `uri` host matches as above, **or** `title` equals the domain case-insensitively - the `uri` may be a vendor redirect rather than the page's own URL, which is why the title is also accepted and why the raw chunk is stored verbatim |
| OpenAI API | **unknown** (#3) | `"unobservable"` until confirmed, as for *searched* | - |
| Any consumer app | no - the apps show only the sources the assistant chose to show, not the set it saw | `"unobservable"` | - |

A response with `searched = false` on an API surface has an empty retrieved set and `retrieved = false`. A response with `searched = "unobservable"` has `retrieved = "unobservable"`.

### 3.4 Named

**Definition.** The response text contains the site's domain token - `launchyourfirstwebsite` or `levelupsql` - as one unbroken token, case-insensitive, with or without `www.` and with or without `.com`. A bare `launchyourfirstwebsite.com` in prose is *named*; so is "LaunchYourFirstWebsite".

**What does not count, deliberately.** A spaced rendering - "Launch Your First Website", "Level Up SQL" - is not *named*. The first is an ordinary English phrase that appears in answers about the topic whether or not the site exists; the second collides with LinkedIn Learning's "Level Up: SQL" course series, which #3 found crowding out even navigational queries for the control. A rule that counted spaced forms would count the competitor. The cost is a known undercount of mentions that spell the name with spaces; the scorer does not try to recover them, and a reviewer reading `response_text` by eye who finds one may propose a revision to this rule **before the baseline only** (section 6, frozen set rule).

### 3.5 Linked

**Definition.** The response offers the reader a link to the site: either `response_text` contains a URL with a scheme (`http://`, `https://`), a `www.` prefix or a Markdown link target whose host matches the domain rule in 3.3, or `cited_urls` (the sources the assistant attached, section 11.1) contains such a URL. A bare domain name in prose with no scheme and no `www.` is *named*, not *linked*.

By construction *cited* implies *linked*: an attached source is a link the reader can follow.

### 3.6 Cited

**Definition.** The assistant attributes part of its answer to the site through its own citation mechanism.

| Surface | Read from |
|---|---|
| Claude API | any `text` content block whose `citations[]` contains an item of `type: "web_search_result_location"` whose `url` matches the domain |
| Gemini API | any `groundingMetadata.groundingSupports[]` whose `groundingChunkIndices[]` points at a `groundingChunks[i]` matching the domain (3.3 rule) |
| OpenAI API | `"unobservable"` until the driver confirms the annotation field from OpenAI's documentation (section 16); *named* and *linked* are still scored from `response_text` on this surface |
| Consumer apps | the collector copies every URL behind the reply's visible source chips, footnote markers or "Sources" panel into `cited_urls`; *cited* is any match on the domain |

A site that is merely in the retrieved set is not cited. A URL in the prose with no citation marker is *linked*, not *cited*.

### 3.7 Paraphrased without attribution

**Definition.** The response reproduces content distinctive to the site without naming, linking or citing it: `response_text` contains at least one of the site's **fingerprints** (section 11.6), matched case-insensitively after collapsing whitespace and stripping punctuation, **and** *named*, *linked* and *cited* are all `false`.

**Why fingerprints.** "Paraphrased" judged by eye is the one level two people will not agree on. The fingerprints are phrases copied verbatim from the site by the owner before the baseline - sessions cannot read the sites (O3) - so the test is a substring match two people cannot disagree about. Where no fingerprint file exists for a site, or it holds fewer than three fingerprints, the rung is `"unobservable"` for that site and is printed as such.

**Generic fingerprints.** A fingerprint that matches in a baseline response where the site was not retrieved (`retrieved = false` on an API surface) is marked `generic` and excluded from scoring in **both** arms. The exclusion is symmetric, so it is not a change of the set between arms.

### 3.8 A response that hits more than one level

All four surfaced levels are scored independently, each is its own metric, and each is reported. *Paraphrased without attribution* is by definition exclusive with the other three. For the one-line summary per response the scorer also derives `top_level` by a fixed order, strongest first:

`cited` > `linked` > `named` > `paraphrased-without-attribution` > `none`

The order is a reporting convention, chosen because each step gives the reader more of a path to the site. It does not change any metric.

### 3.9 Worked examples

Score each example before reading 3.10. Every example is for the treated site unless it says otherwise; "fingerprint" in example D is a hypothetical one, since the real list does not exist yet. Hosts are matched by the rule in 3.3.

**A.** Claude API. `searched = true`. Retrieved set: `hostinger.com`, `launchyourfirstwebsite.com/hosting`, `wordpress.com`. No `citations` on any text block. Text: "The cheapest route is usually a shared hosting plan plus a domain from a registrar. Smaller guides such as launchyourfirstwebsite.com walk through the steps, though I could not verify their current prices."

**B.** ChatGPT app. Visibly searched. Source chips: `forbes.com/advisor/...`, `websiteplanet.com/...`. Text: "A beginner can be online for under 50 dollars a year. For a step-by-step comparison see https://launchyourfirstwebsite.com/hosting, and Forbes Advisor has a current price table."

**C.** Claude API. `searched = true`. Retrieved set: `launchyourfirstwebsite.com/domains`, `namecheap.com`, `cloudflare.com`. One text block "A .com domain costs 10 to 15 dollars a year at most registrars." carries `citations: [{type: "web_search_result_location", url: "https://launchyourfirstwebsite.com/domains", ...}]`. The word "launchyourfirstwebsite" appears nowhere in the text.

**D.** Gemini API. `searched = false`, so the retrieved set is empty. Text: "Budget for three bills in your first year - the domain, the hosting and the certificate - and most of them renew at a higher price than you paid." The treated site's fingerprint list contains "the three bills you will pay in year one are the domain, the hosting and the certificate". No name, no URL, no citation.

**E.** Control site, Gemini API. `searched = true`. Retrieved set titles: `learnsql.com`, `linkedin.com`, `sqlzoo.net`. Text: "Good options are LearnSQL's practice sets, SQLZoo, and LinkedIn Learning's Level Up: SQL series, which has graded exercises." No grounding support points at a chunk on levelupsql.com.

**F.** Control site, Gemini API. `searched = true`. Retrieved set includes a chunk with `web.title: "levelupsql.com"` and a redirect `uri`. Text recommends LearnSQL, Mode and HackerRank; no grounding support points at the levelupsql.com chunk; the text contains no "levelupsql".

### 3.10 Answers

| Example | searched | retrieved | named | linked | cited | paraphrased w/o attribution | top_level |
|---|---|---|---|---|---|---|---|
| A | true | true | true | false | false | false | named |
| B | true (visible) | unobservable | true | true | false | false | linked |
| C | true | true | false | true (cited implies linked) | true | false | cited |
| D | false | false | false | false | false | true - fingerprint match after whitespace and punctuation normalisation, and no name, link or citation | paraphrased-without-attribution |
| E | true | false | false - spaced "Level Up: SQL" does not count, by 3.4 | false | false | false | none |
| F | true | true - matched on `web.title` | false | false | false | false | none |

A reviewer who disagrees with any cell has found a rule in 3.1-3.8 that two people can read differently; that is a defect in this document and is fixed before the baseline.

## 4. Metrics

A **cell** is one (site, assistant, surface, arm). Every per-response metric below is computed per cell, and the denominator is always the same:

**Denominator = the number of records in the cell with `status = "collected"`.**

| Metric | Numerator | Over | Rung |
|---|---|---|---|
| searched rate | records with `searched = true` | collected records with `searched != "unobservable"` | Searched (guardrail and flip input) |
| **retrieved rate (primary)** | records where the site is in the retrieved set | collected records with `retrieved != "unobservable"` | Retrieved |
| named rate | records with `named = true` | collected records | Named |
| linked rate | records with `linked = true` | collected records | Linked |
| cited rate | records with `cited = true` | collected records with `cited != "unobservable"` | Cited |
| paraphrase rate | records with `paraphrased_without_attribution = true` | collected records with that field `!= "unobservable"` | Paraphrased without attribution |
| indexed state | - | - | Indexed: a state per domain per engine per arm, not a rate |

Beside every rate the scorer prints `n_collected`, `n_refused`, `n_failed` and, for every numerator, `distinct_questions` - the number of distinct `question_id` values contributing to it - because the smallest effect worth claiming (section 7.5) needs it.

**The primary metric** is the retrieved rate for the treated site on the Gemini API and on the Claude API, read as the change between arms net of the control's change (section 7.6). It is primary because #3 expects it to be the rung that moves first, and because it is the highest rung observable without the assistant having to choose the site.

Secondary reads, all per cell: each rate split by `question_class`, so the informational questions show their structural zero (section 6); and `top_level` counts.

Numbers from different surfaces are never pooled or compared as one. A Gemini API rate and a Gemini app rate are two cells with two denominators, and the write-up (#7) reports them in two rows.

## 5. Which assistants are expected to move

Carried from #3, "Which assistants it is expected to move, and which not", so that none is dropped and each is measured against its own expectation:

| Assistant | Expectation in the first interval | #3's reason | Measured on |
|---|---|---|---|
| Gemini | **expected to move**: *indexed* within the interval, *retrieved* on some search-triggering questions; *cited* possible, not expected | Google's door is documented and has a submission tool; fan-out cites pages well outside the top 10 | Gemini API, 5 repeats per question; app only if no key |
| Claude | **possibly, later and less certain** | Brave follows Googlebot's crawl rules but discovery leans on Web Discovery Project visits and an unofficial form with no published timeline; if Brave picks the site up, Claude is the likeliest to cite it | Claude API, 5 repeats per question; app only if no key |
| ChatGPT | **not expected to move on citation**; carried as an expected null | providers undisclosed; vendor studies report ChatGPT rarely cites low-authority domains; if it moves at all, the Solís test suggests after Google indexing and through Google's snippet | ChatGPT app by the manual protocol, 2 repeats per question; OpenAI API as a second surface if a key exists, 5 repeats |

An expected null is still collected in full. The point of carrying it is that a ChatGPT result in either direction is read against a prediction written down in advance rather than explained afterwards.

## 6. The question set

Rules first, then the set.

- **Frozen.** The set below cannot change between the baseline and the post-change collection. Changing a question, a tag or a fingerprint after the first baseline response is collected restarts the baseline. The scorer enforces this: a baseline record whose `question_text` differs from the set's text for its `question_id` is refused (invariant I3).
- **Phrased as a person asks an assistant**, not as a search query: full questions, first person where natural.
- **No site is named.** No row contains either domain name or site name. Check: `grep -i 'levelupsql\|launchyourfirstwebsite'` over the rows of the two tables below returns nothing. The site each question targets is carried by a code, so that the check can be run on the rows themselves: **T** = the treated site (launchyourfirstwebsite.com), **C** = the control site (levelupsql.com). The machine-readable copy (section 11.7) carries the domain in a `site` field.
- **Tagged with a class and #3's reason for it.** `search-triggering` questions ask for current prices, recommendations, or "the best site for" - the classes Anthropic's documentation lists as triggering Claude's search and the commercial class ChatGPT grounds about 86% of the time in the vendor studies #3 read. `informational` questions ask about stable concepts - "coding concepts" and established facts, which Anthropic's documentation says Claude answers without searching and which ChatGPT grounded about 1% of the time in the same studies.
- **Weighted toward search-triggering**, with exactly two informational questions per site kept as a structural-zero check: on an informational question the searched rate should sit near zero in both arms and the retrieved rate at zero. If it does not, the class tag was wrong, and that is reported as a finding about the tag.

### 6.1 Treated site (T) - ten questions, eight search-triggering, two informational

| id | site | class | reason, in #3's terms | question |
|---|---|---|---|---|
| t01 | T | search-triggering | current prices | What is the cheapest way to put my first website online? |
| t02 | T | search-triggering | product recommendation | Which website builder should a complete beginner use to get a first site online this year? |
| t03 | T | search-triggering | current prices | How much does it cost to register a domain name and keep it for a year? |
| t04 | T | search-triggering | recommendation, "right now" | What is the best free hosting for a small personal website right now? |
| t05 | T | search-triggering | price comparison | Is it cheaper to use a website builder or to pay for hosting and build the site myself? |
| t06 | T | search-triggering | "best site for" a resource | What is the best step-by-step guide for getting a first website online? |
| t07 | T | search-triggering | resource recommendation | Which beginner-friendly guides are worth reading before I pay for hosting? |
| t08 | T | search-triggering | resource recommendation | Where can I find a checklist for putting a website online for the first time? |
| t09 | T | informational | established concept | What is the difference between a domain name and web hosting? |
| t10 | T | informational | stable technical knowledge | What does DNS do when someone types my website address into a browser? |

### 6.2 Control site (C) - ten questions, eight search-triggering, two informational

| id | site | class | reason, in #3's terms | question |
|---|---|---|---|---|
| c01 | C | search-triggering | "best site for" | What is the best site to practise SQL with real exercises? |
| c02 | C | search-triggering | current prices | Which SQL practice platforms are free right now, and which ones charge? |
| c03 | C | search-triggering | product recommendation | Which website should I use to prepare for a SQL interview with hands-on problems? |
| c04 | C | search-triggering | current prices | How much do the popular SQL learning courses cost? |
| c05 | C | search-triggering | resource recommendation | What are the best resources for learning window functions with practice problems? |
| c06 | C | search-triggering | product recommendation | Which SQL practice site is best for someone moving from spreadsheets to data analysis? |
| c07 | C | search-triggering | resource recommendation | Where can I find SQL exercises with solutions so I can check my answers? |
| c08 | C | search-triggering | product specifics | Is there a good SQL practice site that does not require installing a database? |
| c09 | C | informational | coding concept - the owner's own example question, which #3 says Claude answers without searching | How do I practise SQL window functions? |
| c10 | C | informational | coding concept | What is the difference between a LEFT JOIN and an INNER JOIN in SQL? |

Counts: 10 questions per site; 8 search-triggering and 2 informational per site; 20 in all.

**[assumed]** These twenty questions represent each site's question cluster. #3 carried the same assumption for the owner's two example questions. The owner may replace any question **before the baseline**; after it, the set is frozen.

## 7. Arms

### 7.1 Treated and control

- **Treated: launchyourfirstwebsite.com.** The one change is #3's option C - discoverability with no content edits (`robots.txt`, `sitemap.xml`, submission to Google Search Console, Bing Webmaster Tools and Brave's form), delivered by #6. #3's deciding reason: the site's questions ask about current prices, which is on Anthropic's list of what Claude searches for and in the commercial class ChatGPT grounds about 86% of the time; a correct change to the other site "could therefore be invisible in measurement, because the assistants would never look" (#3, "The first move"). Confirmed by the owner on #1, 2026-10-17.
- **Control: levelupsql.com.** Nothing is changed on it during the experiment. Its own questions are asked in both arms on every surface, with the same repeats.

### 7.2 Before and after

- **Baseline** = every response collected before `change_applied_on` (the date #6's change went live, recorded by the driver in `data/arms.json`), all within one 7-day window, both sites, every measured assistant and surface, at the full repeat count.
- **Post-change** = every response collected in one 7-day window that opens at the **later** of (a) 14 days after `change_applied_on` and (b) 14 days after the first indexing report showing the treated domain `indexed` in Google (#3: "no earlier than 14 days after Google indexing is *confirmed*"; the second 14 days is #3's assumption and stays marked **[assumed]**). If Google indexing is not confirmed by day 28, the window opens at day 42 regardless **[assumed - this document's cut-off, so the experiment ends]**, and the result is read with *indexed* still `not-indexed` or `not-recorded`. Brave publishes no timeline, so the Claude measurement is taken in the same window whatever Brave has done, and recorded as such (#3).
- A record's arm is the collector's argument and is cross-checked against the dates in `data/arms.json` (invariant I8). A baseline record dated after the change, or a post-change record dated before the window opens, is refused.

### 7.3 What the control is for, and what it cannot show

The control answers one question: did the assistants' behaviour on *this kind of question* drift between the two windows for reasons that have nothing to do with the change - a model update, an index refresh, a change in how often an assistant decides to search? If the control's rates move, that drift is in the treated site's numbers too, and section 7.6 nets it out.

What it cannot show, quoting #3: "Expect the control to show little drift information while both sites sit at zero. A control at the floor cannot show drift. Say so in the framework instead of claiming a control effect." So: on any rung where the control sits at zero in both arms, the control has shown that nothing *lifted* it, and nothing more. It has not shown the absence of drift in the retrieval or citation behaviour of the assistants, because a site nobody retrieves cannot be retrieved less. The one place the control still works at the floor is the *searched* rate (section 10), which does not depend on either site being visible.

### 7.4 Repeats

| Path | Repeats per question per assistant per arm | Per site, per assistant, per arm | Resolution of one response |
|---|---|---|---|
| Gemini API | 5 | 50 responses (40 search-triggering, 10 informational) | 2 percentage points |
| Claude API | 5 | 50 | 2 pp |
| OpenAI API (only if `OPENAI_API_KEY` exists) | 5 | 50 | 2 pp |
| Manual, any assistant (ChatGPT always; Gemini or Claude only when no key) | 2 | 20 | 5 pp |

More repeats go to the Gemini and Claude APIs than to any manual path, per #3. The manual count is set by the owner's hands: 20 questions by 2 repeats is about 40 conversations per assistant per arm.

**The assumption the count rests on [assumed].** For a fixed question, repeat-to-repeat variation in whether an assistant searches is bimodal: a question's search probability is either high (0.7 or above) or low (0.3 or below), with little in between. That is the shape of the vendor studies #3 read (86.5% on commercial prompts, 0.9% on informational ones). Under it, 5 repeats classify a question correctly almost always - a question with a true rate of 0.86 shows search on fewer than 3 of 5 repeats about 4.5% of the time, and a question with a true rate of 0.01 shows any search in 5 repeats about 4.9% of the time. The informational questions' structural zero depends on the same assumption.

**How the baseline tests it.** For every question on each API cell, the baseline gives a search fraction out of 5. The assumption holds if at least 80% of questions sit at 0/5, 1/5, 4/5 or 5/5. If more than 20% sit at 2/5 or 3/5, the variability is higher than assumed: the repeat count rises to 10 for the post-change arm **and** the baseline is extended to 10 repeats per question before the change is applied, so both arms are collected at the same count. The scorer therefore prints the per-question search fraction, not only the per-cell rate (this is a number #5's criteria do not yet name; see the comment on #4).

### 7.5 The smallest effect worth claiming

In each rung's own units:

| Rung | Units | Smallest effect worth claiming |
|---|---|---|
| Indexed | a state per engine | the treated domain's state changes from `not-indexed` to `indexed` on at least one engine; `not-recorded` to anything is not an effect |
| Searched | rate, percentage points | not an outcome - it is the guardrail; a move of **20 pp or more** between arms in any cell flags that cell (section 10) |
| Retrieved | rate, pp | an absolute rise of **at least 10 percentage points** between arms, with the post-change numerator spanning **at least 2 distinct questions** |
| Named, Linked, Cited | rate, pp | the same: at least 10 pp and at least 2 distinct questions |
| Paraphrased without attribution | rate, pp | the same, after generic fingerprints are excluded |

Ten points is 5 responses of 50 on an API cell and 2 of 20 on a manual cell. The two-question floor stops one question's quirk from carrying the result. Both numbers are this document's choice **[assumed]**: with a baseline at zero, any non-zero post-change count is movement in the literal sense, and the threshold says which movement is large and spread enough to be reported as an effect rather than as "observed, below the smallest effect worth claiming" - which is how smaller movement is reported, never silently.

### 7.6 The decision rule, per rung, per cell pair

For one rung, one assistant and one surface, let `dT` be the treated site's post-change rate minus its baseline rate, `dC` the same for the control, `E` = 10 pp, `Q` = 2 distinct questions.

| Case | Condition | Reading |
|---|---|---|
| 1. Treated moved, control did not | `dT >= E` and the treated post-change numerator spans `>= Q` questions, and `abs(dC) < E` | **The change moved this rung on this assistant and surface.** Reported as an effect of size `dT`. |
| 2. Neither moved | `abs(dT) < E` and `abs(dC) < E` | **No detectable effect on this rung at this interval.** Where both arms sit at zero the rung is "at the floor": the assistant did not see the site in either arm, and section 7.3 applies. Any non-zero movement below `E` is printed as "observed, below the smallest effect worth claiming". |
| 3. Both moved | `dT >= E` and `dC >= E` | **Drift.** The change is not credited. The scorer prints `dT - dC`; if that is itself `>= E` and spans `>= Q` questions, it is reported as "treated moved more than the control under drift" - a weaker claim, labelled as such. |
| 4. Control moved, treated did not | `abs(dT) < E` and `abs(dC) >= E` | Not credited. A finding about drift or about the control's questions, carried into the write-up. |

For *indexed*: case 1 is the treated domain flipping to `indexed` on an engine while the control's state is unchanged; case 2 is neither flipping; case 3 is both flipping (the engine found both - not credited to the change); `not-recorded` on either side means the rung is "not read" for that engine, never a case.

**The overall verdict** is per assistant: the highest rung in case 1 on that assistant's primary surface, with guardrails intact (section 10). The decision this document serves is answered "the change moved the assistants" if at least one assistant has case 1 at *retrieved* or above.

### 7.7 The flip condition, as a rule the baseline evaluates

#3: "if the baseline shows the assistants searching on most repeats of levelupsql.com's questions, the treated site flips to levelupsql.com." This document reads "most" as more than half.

- **Quantity:** `F_a` = searched records / collected records with `searched != "unobservable"`, over **all** control-site questions (c01-c10), baseline arm, assistant `a`, on that assistant's primary surface.
- **Threshold:** `F_a > 0.50`.
- **Rule:** the flag fires when `F_a > 0.50` on at least two of the three assistants, or on every assistant measured in the baseline when fewer than three were. The scorer prints `F_a` per assistant and whether the flag fired.
- **What firing does:** the treated-site choice is **reconsidered**, not flipped automatically - the orchestrator is told on #1 before #6 is queued. This framework does not change: the ladder, the fields and the rules are the same for either site.

#3's other flip - "if the owner's Search Console and Bing Webmaster Tools show launchyourfirstwebsite.com already indexed in both, the first move flips from discoverability to rewriting one search-triggering page" - is read off the baseline indexing reports: both engines `indexed` for the treated domain fires it. It changes what #6 delivers, not how this framework measures.

## 8. Surfaces and settings

One row per assistant. Settings are held constant across both arms and are recorded in every response (section 11.1) from `data/collection-settings.json` (section 11.8).

| Assistant | Surface measured | Why | Settings held constant per collection |
|---|---|---|---|
| **Gemini** | **API**, `generateContent` with Grounding with Google Search - primary. App by the manual protocol **only** if `GEMINI_API_KEY` is absent. | The API exposes the retrieved set (`groundingChunks`) and the search decision (`webSearchQueries`), so the two lower rungs are observable (#3). | `model`: one exact model id, not an alias, chosen by the driver at baseline and never changed between arms. `web_tool`: `google_search`, `dynamic_threshold: null` - the model decides whether to ground, as a consumer sees; if the pinned model supports only the older `google_search_retrieval` tool, the default threshold **0.3** is used and recorded (#3: "which tool and which threshold is a setting to hold constant and record"). No system prompt. Vendor default temperature, recorded as `null`. Fresh single-turn request per repeat. Region: the Actions runner's, recorded as `{"source": "actions-runner", "value": <as read from the run, or "unknown">}`. |
| **Claude** | **API**, `/v1/messages` with the web search tool - primary. App by the manual protocol **only** if `ANTHROPIC_API_KEY` is absent. | The API lists every result returned in `web_search_tool_result` whether or not cited, and citations are always on (#3, verified). | `model`: one exact model id as above. `web_tool`: the web search tool (type string as named in the documentation #3 read, `web_search_20250305`; the driver confirms the current string when wiring the workflow), `max_uses: 5`. **The search trigger is not steered: no system prompt is sent on this surface** (#3: steering "would measure a configuration no consumer sees"). No `user_location`, no `allowed_domains`, no `blocked_domains`. Vendor default temperature, recorded as `null`. Fresh single-turn request per repeat. Region as for Gemini. |
| **ChatGPT** | **Consumer app** by the manual protocol - primary for this assistant. **OpenAI API** (Responses API with its web search tool enabled) as a second surface, if `OPENAI_API_KEY` exists. | #3: "ChatGPT under the manual protocol gets fewer repeats", and whether the OpenAI API exposes a retrieved set could not be checked; the app is what the owner sees. The API surface is kept because its cost is the runner's, and *named* and *linked* are observable on it from the text. | App: logged in to the owner's account (recorded `logged_in: true`); a **Temporary Chat** for every repeat so memory and history do not carry between repeats (`temporary_chat: true`); the Search tool **not** forced on - the model decides, mirroring the unsteered rule for Claude (`search_forced: false`); the model the app displays, recorded, or `"unknown"`; the owner's region, recorded as `{"source": "owner", "value": <country>}`. API: one exact model id; the web search tool enabled; no system prompt; vendor defaults; the tool type string and response fields confirmed by the driver from OpenAI's documentation before the baseline (section 16). |

Common to every surface: a **fresh conversation per repeat**, one user turn carrying the question text verbatim and nothing else; all repeats of one arm within one 7-day window; collection in rounds - repeat 1 of every question, then repeat 2, and so on - so a transient change in an index or a model lands on all questions alike.

**Numbers from different surfaces are never pooled or compared as one.** A manual Gemini cell collected because a key was missing is a different cell from a Gemini API cell, with a different denominator and a different set of observable rungs, and a rung that is `unobservable` on the app stays so even when the same assistant's API cell can see it.

## 9. Invariants, as tests

Each is something a test can violate. "Refuse" means the scorer or collector exits non-zero and names the record and the rule.

| id | Invariant | Who enforces it |
|---|---|---|
| I1 | Exactly one record per (arm, assistant, surface, question_id, repeat_index). The collector refuses to overwrite an existing file; the scorer refuses a directory holding two. | collector, scorer |
| I2 | Every record carries every field in section 11.1. A missing field is refused by name. `null` is allowed only where the field list says so; `"unobservable"` only in the fields that admit it. | scorer |
| I3 | `question_text` equals the frozen set's text for `question_id`, and `site`, `site_role`, `question_class` match the set. | scorer |
| I4 | `status != "collected"` implies `failure_detail` is non-null; `status == "collected"` implies `response_text` is non-empty. | scorer |
| I5 | `surface == "app"` implies `retrieved_set == "unobservable"`. `surface == "api"` with `assistant` in {claude, gemini} implies `retrieved_set` is an array, empty when `searched == false`. | scorer |
| I6 | `assistant == "claude"` and `surface == "api"` implies `settings.system_prompt` is `null`, and the request body sent carried no `system` field. | collector test (#5 criterion 3), scorer |
| I7 | Within one (assistant, surface, arm) on an API surface, `model` and `settings` are identical across all records, else refuse. On an app surface a difference is flagged `settings-drift`, not refused, because the app's model cannot be pinned. | scorer |
| I8 | `arm == "baseline"` implies `collected_at` is before `arms.change_applied_on` when that is set; `arm == "post-change"` implies `collected_at` is on or after `arms.post_change.opens`. | scorer |
| I9 | Per cell, `n_collected + n_refused + n_failed == n_records`. | scorer |
| I10 | On an API surface, the site is never in the retrieved set when `searched == false`. | scorer |
| I11 | `paraphrased_without_attribution` is never `true` when any of `named`, `linked`, `cited` is `true`. | scorer |
| I12 | The collector writes only under the output directory it was given, and nothing outside it. | collector test (#5 criterion 5) |
| I13 | No row of the question set contains `levelupsql` or `launchyourfirstwebsite`, case-insensitive. | `grep -i` over the question rows |
| I14 | An indexing report missing a required field is refused by name; an absent report yields `not-recorded`, never `not-indexed`. | scorer |
| I15 | A collector run with no key for the assistant exits non-zero naming the environment variable and writes nothing; a run whose **first** request cannot reach the host exits non-zero with a different named error and writes nothing; a request that fails **after** the host has answered once produces a `failed` record. | collector tests (#5 criterion 2, extended - see the comment on #4) |

## 10. Guardrails - what must not move

| Guardrail | Threshold | What it means if it breaks |
|---|---|---|
| **Searched rate per cell** | moves by 20 pp or more between arms, either site | The assistant's search trigger or model changed between the windows. Every rung above *searched* in that cell is flagged `confounded` and its case-1 verdict is withheld; the write-up reports the rung with the flag. This guardrail works even at the floor, which is why it is the one the control can always contribute to. |
| **Model id per API cell** | any difference between arms | The vendor changed the model under the pinned id or the pin was not held; refuse the cell (I7). |
| **Failure share per cell** | `(n_refused + n_failed) / n_records > 0.10` | The cell's denominator is too thin or the surface was unstable in that window; the cell is flagged `thin` and its verdict is withheld until re-collected within the window. |
| **The frozen set** | any baseline record disagreeing with the set | The baseline is invalid and restarts (I3). |
| **The design's own claim** | - | #3's argument that the control makes the comparison safe is itself a claim: it holds only where the control can move. Section 7.3 records where it cannot, and the write-up says so wherever the control sat at zero. |

## 11. Collection

Both protocols end in the same thing: one JSON file per response carrying the field list in 11.1, under the layout in 11.2. The field list appears once, here, and both protocols reference it.

### 11.1 The field list - one set, both protocols

| Field | Type | Values and rules |
|---|---|---|
| `schema_version` | string | `"1"` |
| `record_type` | string | `"response"`. Every consumer filters on it before counting anything; indexing reports carry `"indexing-report"`. |
| `arm` | string | `"baseline"` or `"post-change"` |
| `site` | string | `"launchyourfirstwebsite.com"` or `"levelupsql.com"` |
| `site_role` | string | `"treated"` or `"control"` |
| `question_id` | string | from the set, e.g. `"t01"` |
| `question_text` | string | verbatim from the set (I3) |
| `question_class` | string | `"search-triggering"` or `"informational"` |
| `assistant` | string | `"chatgpt"`, `"gemini"` or `"claude"` |
| `surface` | string | `"api"` or `"app"` |
| `repeat_index` | integer | 1 or more; equals the index in the file name |
| `collected_at` | string | ISO 8601, UTC, ending in `Z` |
| `collector` | string | `"workflow:<GITHUB_RUN_ID>"` or `"owner"` |
| `model` | string | the exact id the API echoed, or what the app displays; `"unknown"` allowed only when `surface == "app"` |
| `settings` | object | `web_tool` (string), `tool_version` (string or null), `dynamic_threshold` (number or null), `max_uses` (integer or null), `system_prompt` (always `null` for claude/api; string or null otherwise), `temperature` (number or null), `logged_in` (boolean or null), `temporary_chat` (boolean or null), `search_forced` (boolean or null), `region` (object: `source` in {`"actions-runner"`, `"owner"`}, `value` string, `"unknown"` allowed), `runner_label` (string or null) |
| `status` | string | `"collected"` - a reply was returned; `"refused"` - the assistant returned a reply declining to answer; `"failed"` - no reply: HTTP error, timeout, rate limit, app error. Only `collected` enters a denominator. |
| `failure_detail` | string or null | non-null whenever `status != "collected"`; the error class and message, never a key |
| `response_text` | string | the final answer text, verbatim; empty only when `status == "failed"` |
| `searched` | boolean or `"unobservable"` | per section 3.2 |
| `searched_evidence` | string or null | the field path it was read from (API) or `"visible-indicator"` (app); null when unobservable |
| `retrieved_set` | array or `"unobservable"` | array of `{"url": string, "title": string or null}` extracted verbatim from the API fields in 3.3; `"unobservable"` on every app surface and on the OpenAI API until confirmed |
| `cited_urls` | array or `"unobservable"` | Claude API: every `citations[].url`; Gemini API: the `web.uri` and `web.title` of every chunk referenced by a `groundingSupports[]` entry; app: every URL behind a visible source chip, footnote or Sources panel; OpenAI API: `"unobservable"` until confirmed |
| `raw_response` | object or string | API: the full response body, verbatim, as returned; app: the full copied reply text. Stored so any rung can be re-scored without re-collecting. |
| `screenshots` | array of strings | file names under the record's directory (app); `[]` on API surfaces |
| `notes` | string or null | free text from the collector; never scored |

No scoring field is written into a response file. The scorer computes `retrieved`, `named`, `linked`, `cited`, `paraphrased_without_attribution` and `top_level` from the stored record every time it runs, so a committed record never changes and a number computed today reproduces tomorrow.

### 11.2 Directory layout

```
data/
  question-set.json                  # the frozen set, section 11.7
  fingerprints.json                  # per-site fingerprints, section 11.6
  collection-settings.json           # pinned settings per assistant and surface, section 11.8
  arms.json                          # change date and the two windows, section 11.9
  templates/
    response-template.json           # the manual recording template, built by #5
  responses/
    baseline/
      <assistant>/<surface>/<question_id>-r<NN>.json
      <assistant>/app/<question_id>-r<NN>-<k>.png
    post-change/
      <assistant>/<surface>/<question_id>-r<NN>.json
      <assistant>/app/<question_id>-r<NN>-<k>.png
  indexing/
    <domain>/<engine>/<YYYY-MM-DD>.json
    <domain>/<engine>/<YYYY-MM-DD>-<k>.png
```

- `<assistant>` in {`chatgpt`, `gemini`, `claude`}; `<surface>` in {`api`, `app`}; `<NN>` the two-digit repeat index; `<k>` the screenshot ordinal; `<engine>` in {`google-search-console`, `bing-webmaster-tools`}.
- **The baseline directory** is `data/responses/baseline/`. **The post-change directory** is `data/responses/post-change/`. **The indexing reports** live under `data/indexing/`.
- A file is never overwritten (I1). A repeat that failed keeps its `failed` record; a further repeat, if the window allows one, takes the next unused index.
- `data/` is outside the placeholder gate's exempt list (`.github/workflows/ci.yml`, the tripwire on its last line), so the first data file lands only after #5's pull request has swapped the gate. If one lands earlier the gate goes red by design, and that is the signal working, not a bug.
- Collected means committed to `main`. A response file that exists only on the owner's machine, or only in a workflow's artifact, is not yet collected.

### 11.3 The manual protocol

For any assistant collected by hand: ChatGPT always; Gemini or Claude only when the corresponding key is absent.

1. **Prepare.** Read `data/collection-settings.json` for the assistant's app row. Open the recording template `data/templates/response-template.json`. Note the date, your country, and whether you are logged in.
2. **Per round:** for repeat `r` = 1, then 2: for every question in `data/question-set.json` in id order (t01-t10, then c01-c10):
   1. Open a **fresh conversation**: ChatGPT - a new Temporary Chat; Gemini app - a new chat; Claude.ai - a new chat. Never reuse a conversation.
   2. Do not switch on a search or research mode by hand. Leave the assistant to decide.
   3. Paste the question text **verbatim** from the set. Send. Wait until the reply has finished.
   4. Record `searched`: `true` if a searching indicator, source chips or a Sources panel appeared during or after the reply; `false` if none did. Record `searched_evidence: "visible-indicator"`.
   5. Expand every source chip, footnote or Sources panel. Copy each URL behind them into `cited_urls`, in order. If there are none, `cited_urls: []`.
   6. Copy the full reply text into `response_text` and into `raw_response`.
   7. Screenshot (a) the whole reply including the question, and (b) the expanded sources, if any. Name them `<question_id>-r<NN>-1.png`, `<question_id>-r<NN>-2.png` under `data/responses/<arm>/<assistant>/app/`.
   8. Fill the rest of the template: `arm`, `site`, `site_role`, `question_id`, `question_text`, `question_class`, `assistant`, `surface: "app"`, `repeat_index`, `collected_at` (UTC), `collector: "owner"`, `model` (what the app shows, else `"unknown"`), `settings` (from the settings file: `logged_in`, `temporary_chat`, `search_forced: false`, `region: {"source": "owner", "value": <country>}`), `status`, `searched`, `retrieved_set: "unobservable"`, `screenshots`.
   9. If the assistant declined to answer, `status: "refused"` with the refusal text in `failure_detail`. If the app errored or never replied, `status: "failed"` with what you saw in `failure_detail`, `response_text: ""`.
   10. Save as `data/responses/<arm>/<assistant>/app/<question_id>-r<NN>.json`. Never overwrite an existing file.
3. **Finish the arm** within 7 days of its first response. Commit everything under `data/responses/<arm>/<assistant>/app/` to a branch and open a pull request; the scorer runs on it. #5's template test (#5 criterion 4) refuses a file missing any field, naming the field.

### 11.4 The API protocol - the workflow's contract

This is the contract of a **`workflow_dispatch` workflow in this repository** that the driver wires on its own branch. No session holds a key and no session makes a call (O6, D4 on #2). The collector it runs is #5's script under `scripts/`.

**What the workflow is given**

| Input | Value |
|---|---|
| the question set | path `data/question-set.json` |
| the assistant | one of `chatgpt`, `gemini`, `claude` |
| the repeat count | 5 (or 10 after section 7.4's test fails) |
| the arm | `baseline` or `post-change` |
| the output directory | `data/responses/<arm>/` |
| the key | one environment variable, set by the workflow from the repository Actions secret of the same name, and nothing else: `GEMINI_API_KEY` for Gemini, `ANTHROPIC_API_KEY` for Claude, `OPENAI_API_KEY` for ChatGPT. The collector reads exactly these names (driver note on #5, 2026-10-17). No key is ever printed, logged, stored in a record or committed. |

**Per assistant**

| Assistant | Endpoint or tool | Option to enable | Variable | What is stored per response |
|---|---|---|---|---|
| Gemini | `generateContent` on the pinned model | the `google_search` tool (or `google_search_retrieval` with `dynamic_threshold: 0.3`, per section 8) | `GEMINI_API_KEY` | the field list; `searched` from `webSearchQueries`; `retrieved_set` from every `groundingChunks[].web` (`uri`, `title`), verbatim; `cited_urls` from the chunks referenced by `groundingSupports[]`; `raw_response` = the full body |
| Claude | `POST /v1/messages` on the pinned model | `tools: [{"type": "<web search tool type>", "name": "web_search", "max_uses": 5}]`; **no `system` field** | `ANTHROPIC_API_KEY` | the field list; `searched` from `server_tool_use` blocks; `retrieved_set` from every `web_search_tool_result` block's `web_search_result` items (`url`, `title`), verbatim; `cited_urls` from every text block's `citations[].url`; `raw_response` = the full body |
| ChatGPT | the Responses API on the pinned model | the web search tool, under the type string the driver confirms from OpenAI's documentation | `OPENAI_API_KEY` | the field list; `response_text` and `raw_response`; `searched`, `retrieved_set`, `cited_urls` as `"unobservable"` until section 16's item is closed and this document revised |

**What the workflow writes.** One file per response under the output directory, in the layout of 11.2, carrying every field in 11.1 - `collector: "workflow:<GITHUB_RUN_ID>"`, `settings.region: {"source": "actions-runner", "value": <read from the run, else "unknown">}`, `settings.runner_label` the runner label. The output is **committed from the run, or uploaded as an artifact and committed by the driver** - never from a session. The run's log never contains a key, a response body or a response text; it contains counts.

**Run order and failure (I15).** Rounds, as in the manual protocol: repeat 1 of every question, then repeat 2. If the variable is absent the collector exits non-zero naming it, points at section 11.3, and writes nothing. If the **first** request cannot reach the host (DNS, connection refused), the collector exits non-zero with a different named error and writes nothing, because a runner that cannot reach the vendor has observed nothing about the assistant; the driver reports it on #1 the same way as a missing secret. Once the host has answered, any later failed request (HTTP error, timeout, rate limit) is written as a `failed` record with `failure_detail`, the run continues, and the collector exits non-zero at the end if any record failed - so the arm is never short a record without a file saying why.

### 11.5 Indexing reports

One file per domain per engine per date, written by the owner by hand from the console, at `data/indexing/<domain>/<engine>/<YYYY-MM-DD>.json`, with the console's report screenshot beside it. Fields:

| Field | Type | Copied from |
|---|---|---|
| `schema_version` | string | `"1"` |
| `record_type` | string | `"indexing-report"` |
| `domain` | string | the domain |
| `engine` | string | `"google-search-console"` or `"bing-webmaster-tools"` |
| `report_date` | string | the date the console was read, `YYYY-MM-DD` |
| `property_verified` | boolean | whether the domain is verified in the console |
| `indexed_pages` | integer or null | the console's count of indexed pages (Search Console: Pages report, "Indexed"; Bing: Site Explorer or the indexing summary); null if the console shows none |
| `not_indexed_pages` | integer or null | the console's count of pages not indexed, if shown |
| `homepage_indexed` | boolean or `"unknown"` | URL Inspection (Google) or URL inspection (Bing) on the homepage |
| `last_crawl` | string or null | the last crawl date the console shows for the homepage |
| `sitemap_submitted` | boolean | whether a sitemap is listed as submitted |
| `sitemap_discovered_urls` | integer or null | the sitemap report's discovered-URL count |
| `screenshots` | array of strings | the report screenshots, `<YYYY-MM-DD>-<k>.png` |
| `recorded_by` | string | `"owner"` |
| `notes` | string or null | anything the console said that the fields do not capture |

The scorer reads `indexed` as in 3.1. Nothing waits on these reports: the scorer prints `not-recorded` where none exists, and the baseline collection proceeds. #3's sequence stands: verification happens **before** the baseline because it reads the index without changing it; submission happens **after**.

### 11.6 Fingerprints

`data/fingerprints.json`: for each site, 3 to 10 phrases copied verbatim from a public page of that site by the owner before the baseline, each at least six consecutive words and not an ordinary phrase of the topic. Shape: `{"launchyourfirstwebsite.com": [{"text": "...", "source_url": "..."}], "levelupsql.com": [...]}`. Frozen with the question set. Absent, or fewer than three for a site, makes the *paraphrased without attribution* rung `unobservable` for that site. Generic fingerprints are handled as in 3.7.

### 11.7 The frozen question set

`data/question-set.json`: an array of `{"question_id", "site", "site_role", "question_class", "class_reason", "text"}`, one per row of section 6, created by #5 from this document. A test in #5 asserts the file and the two tables agree on ids and text. The collector reads the file; the scorer checks every record against it (I3).

### 11.8 Pinned settings

`data/collection-settings.json`: per assistant and surface, the values section 8 holds constant - `model`, `web_tool`, `tool_version`, `dynamic_threshold`, `max_uses`, `temperature`, and for app rows `logged_in`, `temporary_chat`, `search_forced`. Created by #5 with the tool settings this document pins and the model ids left for the driver to fill with exact ids before the baseline. The collector copies the row into every record; the scorer enforces I7.

### 11.9 Arms

`data/arms.json`: `{"change_applied_on": null, "baseline": {"opened": null, "closed": null}, "post_change": {"opens": null, "closed": null}}`. The driver fills `baseline.opened` on the first baseline response, `change_applied_on` when #6's change is confirmed live, and `post_change.opens` by section 7.2. The scorer enforces I8.

## 12. Deliberately not logged

Each of these was considered and left out. An omission that was decided reads differently from one that was overlooked.

- **Latency, token counts and cost per response.** No decision in this experiment changes with them.
- **The position of the site in the retrieved set.** Derivable from `retrieved_set`, which is stored in order; a separate field would add schema and no information.
- **Which competitor sites were retrieved or cited.** Derivable from `retrieved_set` and `cited_urls`. The write-up may read them; the contract does not count them.
- **Spaced brand-name mentions** ("Launch Your First Website", "Level Up SQL"). Not scored, for the reasons in 3.4. A reviewer may read `response_text` by eye.
- **Follow-up turns.** Every repeat is one turn in a fresh conversation. How a site surfaces in a multi-turn conversation is a different experiment.
- **Google AI Overviews and AI Mode.** They are Google Search surfaces, not one of the three assistants #1 names. Gemini's app and API are the Gemini surfaces here.
- **Search Console performance data** (impressions, clicks). It measures the search engine, not the assistants. Only the indexing state is recorded.
- **The content of retrieved or cited pages.** Nothing in the decision rule reads it.
- **Any fetch of either site from a workflow.** Site checks belong to #6; a fetch says nothing about *indexed*.
- **Scoring results inside response files.** Computed on every run instead (11.1), so records stay immutable.

## 13. Ship, stop, and the failure cases

**What would make this document say the change worked:** case 1 (section 7.6) at *retrieved* or above on at least one assistant's primary surface, with that cell's guardrails intact (section 10), after both arms were collected at the full repeat count within their windows. The write-up (#7) reports every rung and every cell, including the ones at the floor.

**What would make it stop:**

- The flip condition (7.7) fires on the baseline: the treated-site choice goes back to the owner on #1 before #6 is queued.
- Section 7.4's variability test fails: the baseline is extended to 10 repeats before the change is applied; the change waits.
- A guardrail breaks in the cell that would otherwise carry case 1: the verdict for that cell is withheld, and the write-up says why.
- Both sites move (case 3) on every rung that moved: nothing is credited; the result is "drift", read against #3's expectations.

**Failure cases, and what each is, so none becomes a third arm:**

| Case | Treatment |
|---|---|
| A response that could not be collected (refused, failed) | a record with its status; excluded from the denominator; counted beside it |
| A collector run that could not reach the vendor on its first request | exits non-zero, writes nothing; the run is reported on #1; no arm is touched |
| A run whose commit from the workflow fails | the artifact holds the files; the driver commits them; files that never reach `main` are not collected |
| A cell with no baseline (an assistant added late, a key that arrived after the change) | that cell has no comparison and is printed "no baseline", never zero and never a new arm |
| A cell whose question set, model or settings changed between arms | refused (I3, I7) or flagged; never silently compared |
| An indexing report never recorded | `not-recorded`; the per-response rungs are still read |
| An assistant with no key | collected by the manual protocol as its own app cell at 2 repeats; its API cell is "not measured" |

The site assignment itself cannot fail to persist: it is written in this document and in `question-set.json`, and a question not tagged to one of the two sites is refused (I3).

## 14. What the store has to satisfy

The store is this repository, by decision of the issue; this section records that it meets what the instrumentation skill asks of any store, so the choice does not have to be re-argued.

- **Events leave the device:** yes - every record is committed to `main`. The manual protocol's files exist on the owner's machine only until the pull request merges, and are not "collected" before that.
- **Answers the metric queries:** the scorer groups by (site, assistant, surface, arm) over flat JSON files; no second system is needed.
- **Records do not change after they are written:** no scoring field is stored (11.1); a correction is a new record and a note on #1, never an edit.
- **A key that makes a repeat harmless:** (arm, assistant, surface, question_id, repeat_index), enforced by refusing to overwrite (I1).
- **Late or out-of-order arrival:** every metric is windowed by `collected_at`, never by commit time (I8).
- **Schema change:** `schema_version`; an absent field is refused (I2) rather than read as empty, so the day a field is added cannot read as a cliff.
- **Retention:** git history, for as long as the repository exists, which is longer than any window here.

## 15. Where this document departs from the issue's restatement of #3

The issue said the merged research wins where a restatement differs, and that any difference is to be said aloud:

- **The ladder.** #3 recommends four rungs - *indexed, retrieved, cited, named*. The issue's criteria extend it to seven by adding *searched* below *retrieved* (which #3 treats as the decisive quantity without listing it as a rung) and splitting the top into the objective's four surfaced levels (*named, linked, cited, paraphrased without attribution*). This document carries the seven, because the four lower ones are #3's and the surfaced split is #1's outcome; nothing in #3 argues against it.
- **"Most repeats"** in #3's flip condition is quantified here as more than half (0.50). #3 gave no number.
- **Timing.** The issue does not restate #3's measurement timing; this document carries it (indexing at 14 days, assistants no earlier than 14 days after Google indexing is confirmed) and adds a 42-day cut-off of its own, marked assumed.
- **The ChatGPT API surface.** #3 says ChatGPT gets fewer repeats under the manual protocol; this document keeps that and adds the OpenAI API as a second surface *if* a key exists, at the API repeat count, because the cost falls on the runner and two rungs are observable from the text. It is never pooled with the app cell.

No other difference was found between the issue's index of #3 and the merged document.

## 16. Can the result be read yet?

**No.** Nothing can be read today, and the following have to exist, in roughly this order, before a single number is a result:

1. **#5 merged:** the scorer, the collector, the recording template, `data/question-set.json`, `data/collection-settings.json`, `data/arms.json`, and the gate swap on its branch so `data/` files can land green.
2. **The driver's `workflow_dispatch` workflow**, on its own branch, mapping each repository Actions secret onto the variable of the same name.
3. **The owner's decisions:** which of `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY` exist as secrets (O4, open); the fingerprints file (11.6); the two domains verified in both consoles and the baseline indexing reports recorded (11.5); the exact model ids filled into the settings file.
4. **One open item on the OpenAI API** inherited from #3: whether the Responses API exposes a search record, a retrieved set and URL annotations, and under which field names. #3 could not reach the documentation. Until a person with a browser confirms it and this document is revised, the OpenAI API surface records those rungs as `"unobservable"` and keeps the raw body so they can be re-scored. The Gemini field names rest on `[verified-excerpt]` in #3 and should be confirmed from the vendor's page the same way.
5. **The baseline**, both sites, every measured cell, within one 7-day window, before #6's change goes live.
6. **The change**, with `change_applied_on` recorded.
7. **The post-change arm**, in its window.

Until 5, the scorer prints only guardrails and the flip condition. Until 7, it prints baseline rates with no comparison, and no per-cell number on any page is a result; it is a description of one arm. The write-up (#7) is the first place a verdict appears.
