# 7. Interview talk track

Use this to practise explaining. Say it out loud until you don't need to read it. Describe this
honestly as a practice project you studied and extended; present the project you build yourself
with real APIs as your own work.

## The 30-second version

"It's a pipeline that takes messy lead lists, finds each company's domain, removes non-companies
and duplicates, enriches them from an API, scores them on fit and intent, assigns owners without
taking accounts from existing reps, and upserts them into the CRM, so re-running never creates
duplicates. Tier-A accounts trigger an alert telling the owner why to call today."

## The 2-minute version (walk the diagram)

1. **Sources:** a CSV export, an enrichment API and the CRM API.
2. **Clean:** domain from website or work email; drop personal emails; standardise employees and
   industries.
3. **Dedupe:** on normalised domain, keeping the most complete row.
4. **Enrich:** every API call goes through one retry function: exponential backoff with jitter,
   respects Retry-After, retries 429 and 5xx, never retries other 4xx, gives up after 5 tries.
5. **Score and route:** fit plus intent with reasons; existing owners kept; round-robin by region.
6. **Load:** batch upsert keyed on domain, batches of 10, never writes blanks, the CRM owns name and
   owner. Second run: zero created.
7. **Reliability:** one bad record doesn't stop the run, summary line every run, failure alert,
   dry-run flag, unit tests on the decision logic. A webhook receiver handles CRM events once even
   when they arrive twice.

## Questions they'll ask, and strong answers

| Question | Strong answer |
| --- | --- |
| Why domain as the key? | Names vary across sources; domains are stable. Fallback to email domain when the website is missing; personal domains excluded. |
| What happens if the API rate-limits you? | 429 → wait (Retry-After if given, otherwise exponential backoff with jitter) → retry up to 5 times → give up, log, alert. Batching keeps calls low in the first place. |
| Why not retry a 400? | It's a permanent error; the same request fails the same way. Retrying wastes the rate limit and hides the bug. |
| How do you avoid duplicates in the CRM? | Normalise domains, dedupe before loading, and upsert keyed on a unique domain property, so even a double run is safe. |
| What if the pipeline crashes halfway? | Re-run it. Upserts make it idempotent; alerts don't double-send because they're rebuilt from the run's results. |
| How do you avoid overwriting good data? | Gap-fill only; never send blanks; field ownership (CRM owns name and owner of existing records). |
| What breaks at 10x volume? | Rate limits and run time (batch, throttle, only enrich new or stale companies), memory (process in chunks), alert fatigue (stricter thresholds or digests). |
| How would you test it? | Unit tests on pure functions (domains, parsing, dedupe, score boundaries); dry-run on real data; a small batch before a full run. |
| How do you know it worked? | The summary line; reports (zero duplicate domains, tier counts); alerts when counts drop to zero. |
| Why are the weights what they are? | Starting assumptions from the ICP; I'd validate them against which accounts actually became meetings and deals, then adjust. |
| Where does AI fit? | Only for judgement on messy text, like drafting an opener, with fixed JSON output, validation and a skip-on-failure fallback. Rules do the exact, cheap parts. |
| What would you do with real HubSpot? | Same design: service key, a unique `domain` property, the batch upsert endpoint, respect HubSpot's limits; webhooks via a small app subscribed to the events we act on. |
| What was the hardest bug? | pandas NaN isn't valid JSON, which crashed the CRM write; fixed by converting NaN to None before any API call. Also caught the pipeline overwriting a company name; fixed with field ownership. |

## Connect it to the business every time

End technical answers with the outcome: "...so reps don't call the same company twice",
"...so a new lead reaches a rep in seconds", "...so the CRM stays trustworthy and reps stop keeping
spreadsheets".
