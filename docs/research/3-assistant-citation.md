# How ChatGPT, Gemini and Claude reach the web, and what makes each cite a small site

**Decision this serves:** which single change to apply to which of levelupsql.com and launchyourfirstwebsite.com first, and which assistants and surfaces the measurement framework (#4) should spend its repeats on.

> **Status:** complete for attempt 1 of issue #3, written on 2026-10-16. The comparison stopped moving: the last four sources read (the Wellows domain-authority study, the Solís indexing test, the Gemini dynamic-retrieval docs, the Originality.ai original) changed no ranking. What I would read next is listed at the end. One caveat runs through the whole document. This environment could fetch Anthropic's documentation but not OpenAI's or Google's, so the claims about those two vendors are read through search excerpts and marked as weaker evidence. The first section explains this.

## In five lines

1. The three assistants reach the web through three different doors. Gemini uses Google's index. Claude uses a third-party index, Brave by outside evidence. ChatGPT uses OpenAI's own crawler plus partners it does not name. Only Google's door has a documented way to submit a site.
2. An assistant only cites a page when it decides to search, and the vendors say it often does not. Anthropic's own documentation says Claude answers "coding concepts" without searching. Vendor studies of ChatGPT find that informational prompts almost never trigger search, while commercial prompts nearly always do. levelupsql.com's example question ("how do I practise SQL window functions") is on the wrong side of that line. launchyourfirstwebsite.com's example ("what is the cheapest way to put my first website online") is on the right side.
3. No check this run could perform returned any page from either domain. Their index state could not be determined from here, and the first move is chosen so it is correct whichever way that turns out.
4. The `llms.txt` evidence is consistent and points one way. AI retrieval bots barely request the file (Ahrefs, server logs), which is the mechanism behind the null citation result (SE Ranking). Neither study says anything favourable for a small site.
5. **Recommendation:** treat launchyourfirstwebsite.com first. Make it discoverable to the three indexes without changing any page content. Expect Gemini to move, Claude possibly, and ChatGPT not. Measure indexing at 14 days and the assistants at the earliest 14 days after indexing is confirmed. Change #1's outcome from "cited" to a ladder: indexed, then retrieved, then cited.

## How to read this document

Every claim about reach or eligibility carries one of four marks. The second exists because of the environment fact below.

- **[verified]**: I fetched the primary source and read it, and could quote the line.
- **[verified-excerpt]**: I identified the primary source's URL, but this environment could not fetch it. The claim rests on the search tool's extraction of that page. This is weaker than verified, because an extraction can drop qualifiers. A reviewer with a browser upgrades it by opening the link.
- **[inferred]**: reasoned from something marked above. The basis is named.
- **[assumed]**: neither, and something rests on it anyway. All of these are collected under "Assumptions that carry weight".

### What this run could not reach

The two sites themselves are refused by the network policy (issue constraint O3, decision log #2). The block turned out to be much wider than that. On 2026-10-16, WebFetch failed DNS resolution (`getaddrinfo ENOTFOUND`) for every one of these hosts:

`platform.openai.com`, `developers.openai.com`, `help.openai.com`, `openai.com`, `developers.google.com`, `developers.google.cn`, `ai.google.dev`, `blog.google`, `www.google.com`, `www.bing.com`, `search.brave.com`, `html.duckduckgo.com`, `www.mojeek.com`, `index.commoncrawl.org`, `crt.sh`, `rdap.verisign.com`, `cloudflare-dns.com`, `web.archive.org`, `ahrefs.com`, `seranking.com`, `www.searchenginejournal.com`, `ppc.land`, `simonwillison.net`, `arxiv.org`, `trust.anthropic.com`, `docs.peec.ai`.

It succeeded for `support.claude.com`, `platform.claude.com`, `claude.com` and `github.com`.

So Anthropic is the only vendor whose documentation this document read first-hand. That asymmetry is a property of the run, not of the vendors. Nothing below should be read as "Anthropic documents more". The real reason for any difference is that only Anthropic's pages could be opened.

## The issue, separated

- **Decision (fixed):** which change, which site, which assistants to measure.
- **Constraints (checked, not assumed):**
  - No fetch of either site: confirmed, and the block is wider than the issue says (above).
  - Site source and hosting are unknown: O2 is still unanswered on #2.
  - Classical SEO is out of scope except as the path to a citation. The evidence below says indexing is that path for all three assistants, so it is in scope.
- **Guesses (reframed here):**
  - That `llms.txt` is the lever worth testing. It is not; see the prior-art section.
  - That "cite" is the outcome to measure. It is the last rung of a ladder whose lower rungs are measurable and more likely to move.
  - That the sites are indexed but not cited. This could not be determined.
  - That the three assistants are one problem. This is the most wrong of the four. They use three indexes, and they decide independently whether to search at all.

## ChatGPT

**How it reaches the web:** a combination of OpenAI's own crawler feeding a search index, third-party search providers, and a fetcher that runs when a user asks.

- **Three crawlers, controlled separately.** [verified-excerpt] [OpenAI, Overview of OpenAI crawlers](https://platform.openai.com/docs/bots)
  - `OAI-SearchBot` "is used to surface websites in search results in ChatGPT's search features. Sites that are opted out of OAI-SearchBot will not be shown in ChatGPT search answers, though can still appear as navigational links."
  - `GPTBot` is for training and is controlled independently.
  - `ChatGPT-User` fetches pages when a user asks. It "is not used for automatic crawling" and "is not used to determine whether content may appear in Search."
  - Changes to `robots.txt` that affect search take about 24 hours.
- **Search providers are not named.** OpenAI says ChatGPT search uses "third-party search providers, as well as content provided directly by our partners". [verified-excerpt] [OpenAI, Introducing ChatGPT search](https://openai.com/index/introducing-chatgpt-search/); [OpenAI Help, ChatGPT search](https://help.openai.com/en/articles/9237897-chatgpt-search)
- **"Bing powers ChatGPT" is not a vendor statement.** It rests on 2024 observations that ChatGPT search and Bing showed similar sources ([Windows Latest, 2024-11-01](https://www.windowslatest.com/2024/11/01/chatgpt-search-engine-uses-bing-builds-extension-to-replace-google-in-chrome/); [Seer Interactive](https://www.seerinteractive.com/insights/87-percent-of-searchgpt-citations-match-bings-top-results)). [verified-excerpt]
  - It is contradicted from two directions. Aleyda Solís published a page that Google indexed and Bing never did. ChatGPT could not find it until it appeared in Google, and then answered from Google's snippet ([Solís, 2025-07](https://www.aleydasolis.com/en/ai-search/chatgpt-uses-google-serp-snippets-for-answers/)). [verified-excerpt]
  - A September 2026 study by Peec AI reports that ChatGPT's results come from OpenAI's own index plus at least eight external providers, with Bing appearing mainly in Deep Research ([Peec AI](https://docs.peec.ai/research/chatgpt-search-result-providers)). [verified-excerpt; OpenAI has confirmed neither study]
- **ChatGPT decides for itself when to search.** At launch, the model "mostly decides" when web information would help, and general topics draw on its own knowledge ([MIT Technology Review, 2024-10-31](https://www.technologyreview.com/2024/10/31/1106472/chatgpt-now-lets-you-search-the-internet/)). [verified-excerpt; secondary account of OpenAI's launch]
  - A vendor study of 100 unforced prompts in August 2026 found search grounding on 86.5% of commercial responses and 0.9% of informational ones ([Cloro](https://cloro.dev/blog/chatgpt-grounding-frequency-study/)). [verified-excerpt]
  - An arXiv preprint found the same direction: 18 of 23 commercial prompts and 2 of 55 informational prompts triggered fan-out searches ([arXiv 2609.23162](https://arxiv.org/pdf/2609.23162)). [verified-excerpt]
  - A Graphite study disagrees on the size of the effect. It saw web search in 58% of unforced informational *entity-comparison* prompts ([Graphite](https://graphite.io/five-percent/research/do-not-force-search-prompt-tracking)). [verified-excerpt] The direction holds across all three studies. The informational rate depends on how a prompt is phrased.

**What a site must do to be eligible, per the vendor:** allow `OAI-SearchBot` in `robots.txt`. There is no opt-in, so not blocking it is enough. That is the whole of the published requirement. [verified-excerpt] [OpenAI bots](https://platform.openai.com/docs/bots)

**Searches for any further OpenAI eligibility requirement (indexing prerequisites, a submission tool, a sitemap endpoint) that came back empty:**
- `OAI-SearchBot "ChatGPT search" robots.txt overview of OpenAI crawlers`: returned the bots page and third-party guides, and no OpenAI submission mechanism. Third-party claims that OAI-SearchBot does not render JavaScript, and that citations carry `utm_source=chatgpt.com`, appear in no OpenAI text the search surfaced.
- `ChatGPT search which search engine index Bing third-party search providers OpenAI help center`: OpenAI names no provider and publishes no indexing prerequisite beyond `robots.txt`.
- `OpenAI help "ChatGPT will" "search the web" automatically decide based on what you ask search triggered`: did not return OpenAI's own help text on when search triggers. Only press and forum accounts came back.

**For a small site [inferred, from the above]:** a page reaches ChatGPT search in one of two ways. Either OAI-SearchBot has crawled it into OpenAI's own index, or it appears in an undisclosed partner's results, which the Solís test suggests includes Google. OpenAI documents no way to submit a site for either path.

## Gemini

**How it reaches the web:** Google Search's own index, through Googlebot. Gemini has no separate crawler for retrieval.

- **No extra requirements.** Google's guide for site owners says AI Overviews and AI Mode have no requirements beyond being indexed and eligible to be shown with a snippet in Google Search, and no special optimisation is needed. Both features may use "query fan-out", issuing several related searches to build one response. [verified-excerpt] [Google Search Central, AI features and your website](https://developers.google.com/search/docs/appearance/ai-features)
- **`Google-Extended` is a `robots.txt` token, not a crawler.** It has no user-agent string and fetches nothing. [verified-excerpt via secondary quotation of Google's page] [Google, Common crawlers: Google-Extended](https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers#google-extended); [Marie Haynes](https://www.mariehaynes.com/should-you-use-google-extended-in-robots-txt/)
  - It controls whether content is used for Gemini training **and for grounding in the Gemini app and in Vertex AI**.
  - It "does not impact a site's inclusion in Google Search nor is it used as a ranking signal".
  - AI Overviews are fed by ordinary Googlebot.
  - The consequence: blocking `Google-Extended` keeps a site out of the consumer Gemini app's grounding while leaving it in AI Overviews.
- **The Gemini API exposes what it retrieved.** "Grounding with Google Search" returns `groundingMetadata` containing `groundingChunks` (source URI and title) and `groundingSupports` (which sentence each source supports). The developer is required to display Google Search Suggestions. [verified-excerpt] [Google AI for Developers, Grounding with Google Search](https://ai.google.dev/gemini-api/docs/google-search); [Firebase AI Logic, Grounding with Google Search](https://firebase.google.com/docs/ai-logic/grounding-google-search); [Google Developers Blog, launch post, 2024-10](https://developers.googleblog.com/en/gemini-api-and-ai-studio-now-offer-grounding-with-google-search/)
- **Gemini also decides when to ground.** Under the older `google_search_retrieval` tool, each prompt gets a prediction score for how much it would benefit from the web. Grounding happens only above a threshold, which defaults to 0.3. A threshold of 0 grounds every response. [verified-excerpt] [Google AI for Developers, Grounding](https://ai.google.dev/gemini-api/docs/grounding) Whether the newer `google_search` tool keeps a settable threshold was not confirmed. The search `Gemini API google_search tool "the model" decides whether to search grounding not every prompt dynamic retrieval threshold` returned only the older tool's documentation.

**What a site must do to be eligible, per the vendor:**
- Be crawlable by Googlebot, indexed, and snippet-eligible: no `nosnippet` and no `noindex`.
- Not block `Google-Extended`. This matters for the Gemini app's grounding, not for AI Overviews.

[verified-excerpt, as above]

**[inferred]** Of the three doors, Google's is the only one that is fully documented and has a submission tool, Google Search Console. A site missing from Google's index cannot be cited by any Gemini surface. A site that is indexed is at least eligible. Fan-out widens the pool: in Ahrefs' February 2026 sample, 38% of AI Overview citations ranked in the organic top 10 and 31% ranked nowhere in the top 100 ([Ahrefs](https://ahrefs.com/blog/search-rankings-ai-citations)). [verified-excerpt] So ranking on page one is not required for an AI Overview citation.

## Claude

**How it reaches the web:** a live search tool backed by a third-party search index, plus Anthropic's own crawlers.

- **Three agents, all honouring `robots.txt` including `Crawl-delay`.** [verified] [Anthropic, Does Anthropic crawl data from the web](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler)
  - `ClaudeBot`: training.
  - `Claude-User`: fetches when a user asks. Disabling it "may reduce your site's visibility for user-directed web search".
  - `Claude-SearchBot`: "navigates the web to improve search result quality for users". Disabling it "may reduce your site's visibility and accuracy in user search results".
- **The API web search tool.** "Claude determines when to search based on the prompt", the API runs the searches, and the answer carries citations, which "are always enabled". Each `web_search_tool_result` lists every result returned, with URL, title and `page_age`, whether or not Claude goes on to cite it. The documentation names no search provider. [verified] [Anthropic, Web search tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool)
- **The same page says Claude does not search for the kind of question levelupsql.com answers.** [verified] [same page, "When Claude searches"](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool#when-claude-searches)
  - It does not search here: "Claude answers directly without searching when the request draws on stable knowledge: Established facts, math, science fundamentals, or coding concepts".
  - It does search for "Current prices, rates, scores, or statistics" and "Information about specific organizations, people, or products that might have changed".
  - Triggering "is steerable through your system prompt", which matters for how #4 configures the API.
- **The provider is Brave Search, on outside evidence; Anthropic's documentation does not say so.** [verified-excerpt] [TechCrunch, 2025-03-21](https://techcrunch.com/2025/03/21/anthropic-appears-to-be-using-brave-to-power-web-searches-for-its-claude-chatbot/); [Simon Willison, 2025-03-21](https://simonwillison.net/2025/Mar/21/anthropic-use-brave/)
  - Brave Search appeared on Anthropic's subprocessor list in March 2025.
  - Claude's search parameters were named `BraveSearchParams`.
  - Simon Willison matched Claude's cited results to Brave's results for the same query.
  - A July 2026 analysis says the list still names Brave and now also names a second search-related provider, turbopuffer ([xponent21](https://xponent21.com/insights/claude-web-search-brave-turbopuffer/)). That is uncorroborated, and the subprocessor page itself could not be fetched ([Anthropic Trust Center](https://trust.anthropic.com/subprocessors)).
- **How Brave finds a new site decides whether a small site exists for Claude at all.** Brave's help page says three things. Its crawler "does not advertise a differentiated user agent". It is partly fed by the opt-in Web Discovery Project, in which Brave browser users contribute anonymous visit data. And "if a domain or page is not crawlable by Googlebot, then Brave Search's bot will not crawl it either." [verified-excerpt] [Brave Search Help, Brave Search crawler](https://search.brave.com/help/brave-search-crawler); [Brave, What is the Web Discovery Project](https://support.brave.app/hc/articles/4409406835469)
  - Brave has no webmaster console.
  - A `search.brave.com/submit-url` form exists according to community replies, but no official Brave page describing it was found ([Brave Community](https://community.brave.app/t/how-to-check-brave-search-engine-performance-data/657719)).

**What a site must do to be eligible:**
- **Per Anthropic:** not block `Claude-SearchBot` or `Claude-User`. Anthropic publishes nothing about indexing prerequisites, submission, or how its search index is built. [verified] [Anthropic crawler article](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler)
- **Per Brave, if the outside evidence holds:** be crawlable under Googlebot's `robots.txt` rules, and be discovered, either by Web Discovery Project visits or by the unofficial submission form. [verified-excerpt]

**Searches for Anthropic or Brave documentation that came back empty:**
- `Claude-SearchBot Anthropic search index crawler announced own index`: only third-party bot directories came back, and they disagree on when the bot first appeared (2024 versus June 2026). No Anthropic announcement.
- `Anthropic Claude web search uses Brave Search subprocessor`: returned the outside evidence above. No Anthropic page names Brave.
- `support.claude.com web search Claude.ai enable web search citations how it works`: no support article describing the provider or the index.
- `Brave Search submit-url form search.brave.com/submit-url official`: forum posts only. No official description, and no stated timeline.
- `https://claude.com/crawling/bots.json` (fetched): 40 IPv4 prefixes, created 2026-10-07, with no bot names or purposes.

**[inferred]** For Claude, a small site has to clear two gates before any page content matters. Brave has to have discovered it, and the question has to be one Claude chooses to search for. Anthropic's own list puts SQL how-to questions outside the second gate.

## Indexability of the two domains

Every check below was run on 2026-10-16. "WebSearch" is this run's search tool. Its backing provider is not disclosed inside the run. [assumed] It is Anthropic's web search tool, and therefore Brave by the evidence above. If that holds, the WebSearch rows are the closest available proxy for what Claude's search can see.

| Domain | Engine or tool | Exact query or request | What it returned |
|---|---|---|---|
| levelupsql.com | WebSearch | `site:levelupsql.com` | 10 results, none on the domain. The tool reported that the `site:` operator was not applied. Results: LinkedIn Learning "Level Up: SQL", GitHub course repositories, an Apress book. |
| levelupsql.com | WebSearch | `"levelupsql.com"` | 10 results, none on the domain. The same LinkedIn Learning and "Level Up" results. |
| levelupsql.com | WebSearch | `levelupsql` | 10 results, none on the domain. A name collision with LinkedIn Learning's "Level Up: SQL" series fills the page. |
| levelupsql.com | WebSearch (extended) | `levelupsql.com SQL practice window functions` | 9 results, none on the domain. LearnSQL, machinelearningplus, sqltutorial.org and others. |
| levelupsql.com | Google, via fetch | `https://www.google.com/search?q=site%3Alevelupsql.com` | Could not run: `getaddrinfo ENOTFOUND www.google.com` |
| levelupsql.com | Bing, via fetch | `https://www.bing.com/search?q=site%3Alevelupsql.com` | Could not run: `ENOTFOUND www.bing.com` |
| levelupsql.com | Brave Search, via fetch | `https://search.brave.com/search?q=site%3Alevelupsql.com` | Could not run: `ENOTFOUND search.brave.com` |
| levelupsql.com | DuckDuckGo, via fetch | `https://html.duckduckgo.com/html/?q=site%3Alevelupsql.com` | Could not run: `ENOTFOUND html.duckduckgo.com` |
| levelupsql.com | Mojeek, via fetch | `https://www.mojeek.com/search?q=site%3Alevelupsql.com` | Could not run: `ENOTFOUND www.mojeek.com` |
| levelupsql.com | Common Crawl index | `index.commoncrawl.org/collinfo.json`, then `CC-MAIN-2026-39-index?url=levelupsql.com/*` | Could not run: `ENOTFOUND index.commoncrawl.org` |
| levelupsql.com | Certificate transparency / registry / DNS | `crt.sh/?q=levelupsql.com`, `rdap.verisign.com/.../levelupsql.com`, `cloudflare-dns.com/dns-query?name=levelupsql.com` | Could not run: `ENOTFOUND` for each host |
| launchyourfirstwebsite.com | WebSearch | `site:launchyourfirstwebsite.com` | 9 results, none on the domain. HOSTDOG, HostGator, Elementor, Bluehost and others. |
| launchyourfirstwebsite.com | WebSearch | `"launchyourfirstwebsite.com"` | 9 results, none on the domain. HostGator, Bluehost, daveyandkrista.com and others. |
| launchyourfirstwebsite.com | WebSearch | `launchyourfirstwebsite` | 9 results, none on the domain. Generic first-website guides. |
| launchyourfirstwebsite.com | WebSearch (extended) | `launchyourfirstwebsite.com cheapest way to put my first website online` | 10 results, none on the domain. top10.com, websiteplanet, Forbes Advisor, and a near-namesake, myfirstwebsite.com. |
| launchyourfirstwebsite.com | Google, via fetch | `https://www.google.com/search?q=site%3Alaunchyourfirstwebsite.com` | Could not run: `ENOTFOUND www.google.com` |
| launchyourfirstwebsite.com | Bing, via fetch | `https://www.bing.com/search?q=site%3Alaunchyourfirstwebsite.com&setlang=en` | Could not run: `ENOTFOUND www.bing.com` |
| launchyourfirstwebsite.com | Brave Search, via fetch | `https://search.brave.com/search?q=site%3Alaunchyourfirstwebsite.com` | Could not run: `ENOTFOUND search.brave.com` |
| launchyourfirstwebsite.com | DuckDuckGo, via fetch | `https://html.duckduckgo.com/html/?q=site%3Alaunchyourfirstwebsite.com` | Could not run: `ENOTFOUND html.duckduckgo.com` |
| launchyourfirstwebsite.com | Mojeek, via fetch | `https://www.mojeek.com/search?q=site%3Alaunchyourfirstwebsite.com` | Could not run: `ENOTFOUND www.mojeek.com` |
| launchyourfirstwebsite.com | Common Crawl index | `CC-MAIN-2026-39-index?url=launchyourfirstwebsite.com/*` | Could not run: `ENOTFOUND index.commoncrawl.org` |
| launchyourfirstwebsite.com | Certificate transparency / registry / DNS | `crt.sh/?q=launchyourfirstwebsite.com`, `rdap.verisign.com/.../launchyourfirstwebsite.com`, `cloudflare-dns.com/dns-query?name=launchyourfirstwebsite.com` | Could not run: `ENOTFOUND` for each host |

**levelupsql.com: could not determine.** The one reachable tool returned no page from the domain on four queries. It does not apply `site:`, so this is absence of evidence and not evidence of absence. Every engine-specific check failed to run. Separately from indexing, the brand name collides with LinkedIn Learning's "Level Up: SQL" courses. Even navigational queries for "level up sql" are crowded out. [verified, from the rows above]

**launchyourfirstwebsite.com: could not determine.** The one reachable tool returned no page from the domain on four queries, with the same `site:` caveat. Every engine-specific check failed to run. The pages that did come back for its owner's own example question belong to hosting companies, publishers and a near-namesake. [verified, from the rows above]

**How to settle both in minutes, which this run cannot do:** the owner verifies each domain in Google Search Console and Bing Webmaster Tools and reads the indexing report. Doing so reads the index state without changing it. That is why the recommendation below puts verification *before* the baseline and the submission *after* it.

## The three prior-art claims

These are the issue's guesses, traced to their originals.

**1. "`llms.txt` adoption up 8.8x in a year."**
- **Original:** [Originality.ai, LLMs.txt Tracking Study and Live Dashboard](https://originality.ai/blog/llms-txt-tracking-study). [verified-excerpt; first found through [PPC Land](https://ppc.land/llms-txt-adoption-rises-8-8x-but-97-of-files-get-zero-ai-requests/), then located at the source]
- **Method in one line:** a monthly count of sites serving `/llms.txt` across a tracked set of more than 3 million websites, which went from 4,088 in June 2025 to 36,120 in May 2026.
- **Verdict:** it does not bear on a small site. It counts publishers, not readers. It says nothing about whether any assistant fetches the file or cites the site.

**2. "An Ahrefs log study found 97% of `llms.txt` files received zero requests."**
- **Original:** [Ahrefs, We Analyzed 137K Sites: 97% of llms.txt Files Never Get Read, 2026-06-15](https://ahrefs.com/blog/llmstxt-study/). [verified-excerpt]
- **Method in one line:** across 137,210 domains on Ahrefs' analytics products, it checked for a valid `/llms.txt` (about 38,000 had one) and classified every request to that path in May 2026 by user agent.
- **What it found:** 97% of valid files saw no request that month. AI retrieval bots made about 1.1% of the requests that did occur. The top requesters were GPTBot (training) and Claude-Code (a coding agent), not search or assistant retrieval bots.
- **The authors' own caveats:** the sample skews technical, the study counts requests and not use, and audit tools, including Ahrefs' own, are a large share of traffic.
- **Verdict:** it bears on a small site, and against `llms.txt`. The mechanism it measures, retrieval bots not requesting the file, does not depend on site size. If anything, a small site gets fewer bot visits of every kind. [inferred]

**3. "An SE Ranking study of about 300,000 domains found no citation lift from having one."**
- **Original:** [SE Ranking, Does LLMs.txt impact your AI visibility and citations? No, according to research, 2025-11-07](https://seranking.com/blog/llms-txt/). [verified-excerpt]
- **Method in one line:** it crawled about 300,000 domains for `llms.txt` (10.13% had one) and tested its relationship to how often each domain is cited by LLMs, using correlation tests and an XGBoost model. Removing the `llms.txt` feature *improved* the model's accuracy.
- **Verdict:** it bears weakly. It is cross-sectional, and its population is domains that already carry citation and traffic data, so it cannot speak to a site that is not indexed. For an unindexed site, `llms.txt` is irrelevant by construction, because nothing retrieves anything from it.

**How claims 2 and 3 fit together:** this is the "mechanism that explains a published null" the issue asked about. The Ahrefs log data supplies the reason for SE Ranking's null. Retrieval bots do not fetch the file, so the file cannot reach the step where citation is decided. The two studies came from different firms with different methods and agree on the mechanism. That is stronger than either one alone. [inferred]
- Google's John Mueller made the same point from the vendor side in June 2025: "FWIW no AI system currently uses llms.txt" ([Search Engine Roundtable](https://seroundtable.com/google-ai-llms-txt-39607.html)). [verified-excerpt; secondary report of a Bluesky post]
- I found no critic arguing that `llms.txt` lifts citations with log or citation data behind the claim. The searches were `"llms.txt" critics Google Mueller "no AI system" uses llms.txt statement`, `llms.txt adoption grew 8.8x year`, and `SE Ranking llms.txt study 300,000 domains AI citations`. The supporting voices found were vendors' adoption counts, not effect measurements.

## Candidate interventions

Each option records what it does, what it costs, what it rules out later, and what would have to be true for it to be the right pick.

### A. Change nothing

- **What it does:** keeps the baseline untouched while the measurement framework is built.
- **Costs:** nothing.
- **Rules out later:** nothing. But if the sites are not indexed, it measures a floor of zero, indefinitely.
- **Right pick if:** the baseline shows both sites already retrieved by all three assistants, so the question becomes ranking rather than reach.

### B. Publish `llms.txt` (the issue's candidate)

- **What it does:** adds a Markdown index of the site at `/llms.txt`.
- **Costs:** under an hour.
- **Rules out later:** little, though it would muddy attribution if it were bundled with anything else.
- **Right pick if:** an assistant's retrieval path fetched the file. The Ahrefs logs say retrieval bots barely do, and no vendor among the three documents using it (see above).

### C. Make the site discoverable to the three indexes, without changing any page

- **What it does:** a `sitemap.xml` referenced from `robots.txt`, and a `robots.txt` that explicitly allows `Googlebot`, `OAI-SearchBot` and `Claude-SearchBot` and does not block `Google-Extended`. Then the sitemap is submitted in Google Search Console and Bing Webmaster Tools, and the homepage URL at Brave's submit form.
- **Costs:** about an hour of the owner's hands, because both consoles need account verification on the domain, which only the owner can do (O2). Two small files.
- **Rules out later:** nothing. It is a prerequisite for every other option, and it is harmless if the site is already indexed.
- **Right pick if:** the site is missing from at least one of the three indexes. That cannot be determined from here, and the owner's console verification settles it.

### D. Rewrite one page for citation (statistics, quotations, answer-first; "GEO")

- **What it does:** follows the KDD 2024 paper that reported up to 40% visibility gains from adding statistics, quotations and cited sources ([Aggarwal et al., GEO](https://arxiv.org/abs/2311.09735)). [verified-excerpt]
- **Costs:** a few hours per page.
- **Rules out later:** it changes the page that is measured, so it must come after any discoverability change, or the two effects cannot be separated.
- **Right pick if:** the page is already retrieved. A July 2026 survey of 45 studies finds the paper's gains are "conditional on a source already being present in a fixed context" and "establish neither organic discoverability nor durable traffic effects". It also finds that citation-oriented rewrites can *impair* retrieval ([Martinez, arXiv 2607.14035](https://arxiv.org/pdf/2607.14035)). [verified-excerpt; preprint]

### E. Earn a mention on a page the assistants already cite (the candidate nobody asked for)

- **What it does:** gets the site named on a third-party page that already comes back for the question cluster, such as a curated list, a forum answer or a resource round-up. The assistant then retrieves and cites *that* page, which names the site.
- **Costs:** outreach time, and it is not under the owner's control. It also has to be a genuine recommendation, not a placed one.
- **Rules out later:** a clean attribution. Movement could come from the mention or from the page's own changes.
- **Right pick if:** the site cannot be made retrievable in the window, or is retrievable but outranked. It is the only option that can produce the "named" rung without the site itself being indexed.
- **Evidence:** the strongest correlate of brand visibility in AI Overviews in a 75,000-brand study was branded web mentions (correlation 0.664), ahead of every on-site factor ([Ahrefs, 2025-05-26](https://ahrefs.com/blog/ai-overview-brand-correlation/)). [verified-excerpt; correlational, and restricted to domains with Domain Rating above 40, which neither site is likely to be [assumed]]
- **Why it loses here:** it is slow, it is not a site change (which #1's outcome 4 asks for), and it makes attribution harder.

### Discarded

- **Discarded: getting into training data** (allowing `GPTBot`, `ClaudeBot`, `Google-Extended` and Common Crawl for model training). Neither vendor publishes when crawled content enters a released model, and training cycles are longer than this experiment's window, so no before-and-after measurement could attribute a change to it. The sensible default is still not to block them.
- **Discarded: structured data markup as the first move.** Google says AI features need no special optimisation beyond normal indexing and snippet eligibility ([Google Search Central](https://developers.google.com/search/docs/appearance/ai-features)) [verified-excerpt], and neither of the other two vendors mentions it.

## Recommendation

### Is #1 reasonable as stated for two small sites?

Not as stated. "Get both sites surfaced in ChatGPT, Gemini and Claude answers" quietly assumes three things that the evidence above says are each uncertain or false:

1. Each site is in each assistant's index. This could not be determined, and only Google offers a way to submit.
2. Each assistant searches for the owner's questions. For levelupsql.com's example, Anthropic's documentation says Claude does not, and the ChatGPT studies agree on the direction.
3. Being retrieved leads to being cited. Even for indexed pages, the AI-citation overlap with top-10 results is low (about 8% for ChatGPT against Google's or Bing's top 10, per [Ahrefs](https://ahrefs.com/blog/ai-search-overlap/) [verified-excerpt]). The evidence on small domains conflicts: [Wellows](https://wellows.com/research/does-domain-authority-matter-for-ai-citations/) finds 47.9% of citations go to domains below DA 40, but reports ChatGPT shifting toward stronger domains in July 2026 [verified-excerpt; vendor study].

**Recommended alterations,** which the orchestrator can carry into #4 to #6 without adding scope:
- **Indexability first.** The first change is option C.
- **One site treated, one as the control,** as already planned.
- **A different outcome than citation alone.** A four-rung ladder: *indexed* (per engine), *retrieved* (the site appears in the result set the assistant saw), *cited*, *named*.
  - The *retrieved* rung is directly observable on two of the three APIs. Claude's `web_search_tool_result` lists every result whether cited or not [verified], and Gemini's `groundingChunks` lists sources [verified-excerpt].
  - This turns a likely citation null into a measurement that still says something.
- **A question cluster restricted to questions that trigger search,** with a few informational ones kept on purpose as a structural-zero check.

Not recommended: dropping to one assistant. The three are cheap to run together, and their different doors are themselves the most interesting finding available.

### The first move

**Treat launchyourfirstwebsite.com first.** levelupsql.com is the control.

The deciding reason is the owner's own example questions. "What is the cheapest way to put my first website online" asks about current prices, which is on Anthropic's list of things Claude searches for [verified] and in the commercial class that ChatGPT grounds about 86% of the time [verified-excerpt; vendor study]. "How do I practise SQL window functions" is a coding concept, which Claude answers without searching [verified], and is informational, which ChatGPT grounded about 1% of the time [verified-excerpt].

A correct change to levelupsql.com could therefore be invisible in measurement, because the assistants would never look. A change to launchyourfirstwebsite.com has a path to show up. levelupsql.com also carries a name collision with LinkedIn Learning that this experiment cannot fix.

**The single change:** option C, discoverability with no content edits. Sequence it like this so the baseline stays clean:
1. The owner verifies launchyourfirstwebsite.com, and also levelupsql.com, in Google Search Console and Bing Webmaster Tools, and records each indexing report. This resolves "could not determine" for both domains without changing anything.
2. #5 takes the baseline.
3. #6 delivers `robots.txt` and `sitemap.xml` for launchyourfirstwebsite.com, as a patch or as exact edits, since the hosting is unknown (O2). The owner submits the sitemap in both consoles and the homepage at Brave's form, and records the date.

If step 1 shows launchyourfirstwebsite.com is already indexed in Google and Bing, the change shrinks to whatever is missing. If nothing is missing, see the flip condition below.

**Which assistants it is expected to move, and which not:**
- **Gemini: expected to move.** Google's door is documented and has a submission tool, and fan-out cites pages well outside the top 10 [verified-excerpt].
  - Expect *indexed* within the interval and *retrieved* on some search-triggering questions.
  - *Cited* is possible but not expected in the first interval.
- **Claude: possibly, on a slower and less certain timeline.** Brave follows Googlebot's crawl rules, but discovery leans on Web Discovery Project visits and an unofficial submit form, with no published timeline [verified-excerpt; empty searches above].
  - A small vendor analysis reports that Claude cites lower-authority sites at a higher rate than the other assistants ([Stacker](https://stacker.com/blog/low-dr-sites-still-earn-ai-citations)) [verified-excerpt; vendor study]. If Brave picks the site up, Claude is the likeliest to cite it.
- **ChatGPT: not expected to move on citation in the first interval.** The providers are undisclosed. The same Stacker analysis reports ChatGPT rarely cites domains below DR 61, and Wellows reports a July 2026 shift toward stronger domains [verified-excerpt; vendor studies].
  - If ChatGPT moves at all, the Solís test suggests it will be after Google indexing and through Google's snippet [verified-excerpt]. That makes ChatGPT a cheap test of a contested mechanism rather than the main event.

**When to measure:**
- **Indexing:** check each engine 14 days after submission. Google's URL Inspection documentation, as quoted by a third party, says indexing "can take up to a week or two" ([OneLocal, quoting Google](https://onelocal.com/?p=3088)) [verified-excerpt; the Google page itself could not be fetched or found by search, so this is weak]. Metehan Yesilyurt's new-domain test appeared in Google and Bing in about 10 days ([Yesilyurt, 2025-07-18](https://metehan.ai/blog/what-happens-when-you-launch-a-website-without-google-or-bing-ai-citation-test/)) [verified-excerpt].
- **The assistants:** no earlier than 14 days after Google indexing is *confirmed* in Search Console. That puts the earliest measurement around 28 days after the change. The second 14 days is **[assumed]**: no source gives a lag from indexing to assistant retrieval.
- Brave publishes no timeline, so if Brave has not picked the site up by then, the Claude measurement is taken anyway and recorded as such.

**For #4, the measurement framework [inferred, from the sections above]:**
- **Spend most repeats on the Gemini API with Google Search grounding and the Claude API with the web search tool.** Both expose the *retrieved* set, so the second rung is observable there and not only the last one.
- **Do not steer Claude's search trigger** in the system prompt for the primary arm. The documentation says it is steerable, and steering it would measure a configuration no consumer sees.
- **ChatGPT under the manual protocol gets fewer repeats.** Whether OpenAI's API exposes a retrieved set could not be checked, because its documentation was unreachable.
- **Weight the question set toward search-triggering questions:** prices, recommendations, "best site for".
- **Keep a few informational ones** as a structural-zero check.
- **Expect the control to show little drift information while both sites sit at zero.** A control at the floor cannot show drift. Say so in the framework instead of claiming a control effect.

## The case against

**The strongest argument against this recommendation, found by searching for people who tried indexing first:** indexing is necessary and nowhere near sufficient, and launchyourfirstwebsite.com's niche is one of the most crowded on the web.
- An Indie Hackers founder optimised two sites for AI citations for a month and got zero citations. Even after the diagnosis that Google indexing was the gate, they named backlinks and authority as still missing ([Indie Hackers](https://www.indiehackers.com/post/i-spent-a-month-optimizing-two-sites-for-ai-citations-geo-and-got-zero-results-here-s-the-actual-diagnosis-b4ab9e1367)). [verified-excerpt]
- Solís's page was indexed by Google and still was not found by ChatGPT until it surfaced in Google's results ([Solís](https://www.aleydasolis.com/en/ai-search/chatgpt-uses-google-serp-snippets-for-answers/)). [verified-excerpt]
- The pages that came back for the owner's own question (Forbes Advisor, websiteplanet, top10.com, hosting companies, and the near-namesake myfirstwebsite.com) are exactly the high-authority competitors the Wellows data says ChatGPT has been moving toward [verified, from the indexability rows; verified-excerpt for Wellows].

So the likeliest result of the recommended first move is: *indexed* yes, *retrieved* occasionally on Gemini, *cited* nowhere within the window. levelupsql.com faces less crowding on recommendation-style questions ("best site to practise SQL"). Someone who wants a citation gain for the portfolio piece might reasonably pick levelupsql.com with recommendation questions, or option E.

This document's answer is that the ladder makes that null informative: it separates "the assistant could not see the site" from "the assistant saw it and chose others", and that distinction is the experiment's most defensible insight. The cost is real, though. The first wave may well produce no citation at all.

I also searched for people who submitted a sitemap and then lost visibility or regretted it (`site indexed in Google and Bing but still not cited by ChatGPT Claude experiment new site AI citations months`). I found no regret, only the insufficiency reports above. I read that as a safe move, not a sufficient one.

**What would flip the answer:** if the owner's Search Console and Bing Webmaster Tools show launchyourfirstwebsite.com already indexed in both, the first move flips from discoverability to rewriting one search-triggering page (option D); and if the baseline shows the assistants searching on most repeats of levelupsql.com's questions, the treated site flips to levelupsql.com.

## Searches that came back empty, in one place

Each of these is a finding about how thin the ground is, not a gap in effort:

- **No vendor among the three documents a lag** between a site being indexed and it being retrievable by the assistant. I found none in OpenAI's or Anthropic's text (searches listed in their sections), and Google's AI features page states none. This is why the 28-day interval is partly assumed.
- **No official Brave page describes `search.brave.com/submit-url`** (`Brave Search submit-url form search.brave.com/submit-url official`).
- **No Anthropic page names its search provider** (`Anthropic Claude web search uses Brave Search subprocessor`).
- **No OpenAI page names its search providers** or describes when search triggers (`ChatGPT search which search engine index Bing ...`, `OpenAI help "ChatGPT will" "search the web" ...`).
- **No direct replication of the GEO paper on a live assistant** with a small site (`GEO paper critique replication "generative engine optimization" fails real search engines`). The 2026 survey is the nearest, and it is a preprint.
- **No peer-reviewed study of search-trigger rates for coding versus commercial prompts** (`percentage of prompts ChatGPT triggers web search coding questions vs commercial queries study search rate`). Only vendor studies and one preprint.
- **No original Google Search Central page carrying the phrase "a few days to a few weeks"** (`Google Search Central "can take anywhere from a few days to a few weeks" crawl index new page request indexing`). The quoted "up to a week or two" comes via a third party.
- **No study with log or citation data showing `llms.txt` lifting citations** (searches in the prior-art section).

## Assumptions that carry weight

- **[assumed]** This run's WebSearch tool is Anthropic's web search, and therefore Brave-backed. This affects only how the WebSearch rows are read, not the classification.
- **[assumed]** Assistants become able to retrieve a page about 14 days after it is indexed. No source gives this lag, and it sets the measurement interval.
- **[assumed]** The owner's two example questions represent each site's question cluster. If #4's question set for levelupsql.com is mostly recommendation questions, the search-trigger argument for the site choice weakens.
- **[assumed]** Neither site has a Domain Rating above 40. That would put both outside the population of the Ahrefs brand-mention study.
- **[assumed]** The owner can verify both domains in Google Search Console and Bing Webmaster Tools. This needs DNS or file access on hosting nobody here knows (O2).

## What I would read next

If this were continued, these are the next sources, in order:
1. OpenAI's Responses API web search documentation, to learn whether ChatGPT's API exposes a retrieved set the way Claude's and Gemini's do. This decides how many ChatGPT repeats are worth spending. It was unreachable here.
2. Google's crawler overview page directly, to upgrade the `Google-Extended` claims from secondary quotation.
3. The full Martinez survey PDF, for its treatment of the indexing stage.
4. Brave's help pages, for anything on submission timing.

None of these is likely to change the site or the change. Item 1 could change #4's allocation of repeats.

## Sources

Fetched and read, which is the basis for [verified]:
- [Anthropic, Does Anthropic crawl data from the web](https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler)
- [Anthropic, Web search tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool)
- [Anthropic, crawler IP list](https://claude.com/crawling/bots.json)

Identified and read through search extraction, which is the basis for [verified-excerpt]:
- [OpenAI crawlers](https://platform.openai.com/docs/bots), [OpenAI ChatGPT search launch](https://openai.com/index/introducing-chatgpt-search/), [OpenAI Help, ChatGPT search](https://help.openai.com/en/articles/9237897-chatgpt-search)
- [Google AI features and your website](https://developers.google.com/search/docs/appearance/ai-features), [Google common crawlers](https://developers.google.com/search/docs/crawling-indexing/google-common-crawlers#google-extended), [Gemini grounding](https://ai.google.dev/gemini-api/docs/google-search), [Gemini grounding (legacy)](https://ai.google.dev/gemini-api/docs/grounding), [Google Developers Blog](https://developers.googleblog.com/en/gemini-api-and-ai-studio-now-offer-grounding-with-google-search/), [Firebase AI Logic](https://firebase.google.com/docs/ai-logic/grounding-google-search)
- [Brave Search crawler help](https://search.brave.com/help/brave-search-crawler), [Brave Web Discovery Project](https://support.brave.app/hc/articles/4409406835469), [Brave Community on submit-url](https://community.brave.app/t/how-to-check-brave-search-engine-performance-data/657719)
- [TechCrunch on Claude and Brave](https://techcrunch.com/2025/03/21/anthropic-appears-to-be-using-brave-to-power-web-searches-for-its-claude-chatbot/), [Simon Willison](https://simonwillison.net/2025/Mar/21/anthropic-use-brave/), [xponent21](https://xponent21.com/insights/claude-web-search-brave-turbopuffer/)
- [Originality.ai tracking study](https://originality.ai/blog/llms-txt-tracking-study), [Ahrefs llms.txt study](https://ahrefs.com/blog/llmstxt-study/), [SE Ranking llms.txt study](https://seranking.com/blog/llms-txt/), [Search Engine Roundtable on Mueller](https://seroundtable.com/google-ai-llms-txt-39607.html)
- [Ahrefs AI Overview citations and rankings](https://ahrefs.com/blog/search-rankings-ai-citations), [Ahrefs AI search overlap](https://ahrefs.com/blog/ai-search-overlap/), [Ahrefs brand correlation](https://ahrefs.com/blog/ai-overview-brand-correlation/), [Seer Interactive](https://www.seerinteractive.com/insights/87-percent-of-searchgpt-citations-match-bings-top-results), [Peec AI](https://docs.peec.ai/research/chatgpt-search-result-providers), [Windows Latest](https://www.windowslatest.com/2024/11/01/chatgpt-search-engine-uses-bing-builds-extension-to-replace-google-in-chrome/), [MIT Technology Review](https://www.technologyreview.com/2024/10/31/1106472/chatgpt-now-lets-you-search-the-internet/)
- [Cloro grounding study](https://cloro.dev/blog/chatgpt-grounding-frequency-study/), [arXiv 2609.23162](https://arxiv.org/pdf/2609.23162), [Graphite](https://graphite.io/five-percent/research/do-not-force-search-prompt-tracking)
- [Aggarwal et al., GEO](https://arxiv.org/abs/2311.09735), [Martinez, critical survey of GEO](https://arxiv.org/pdf/2607.14035)
- [Wellows domain authority study](https://wellows.com/research/does-domain-authority-matter-for-ai-citations/), [Stacker low-DR study](https://stacker.com/blog/low-dr-sites-still-earn-ai-citations)
- [Solís test](https://www.aleydasolis.com/en/ai-search/chatgpt-uses-google-serp-snippets-for-answers/), [Yesilyurt test](https://metehan.ai/blog/what-happens-when-you-launch-a-website-without-google-or-bing-ai-citation-test/), [Indie Hackers report](https://www.indiehackers.com/post/i-spent-a-month-optimizing-two-sites-for-ai-citations-geo-and-got-zero-results-here-s-the-actual-diagnosis-b4ab9e1367), [OneLocal quoting Google](https://onelocal.com/?p=3088), [Marie Haynes on Google-Extended](https://www.mariehaynes.com/should-you-use-google-extended-in-robots-txt/)
