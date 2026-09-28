# Reddit Subreddit Media-Buying Planner

Use a bounded sample of public posts from marketer-selected subreddits to decide where to consider a small Reddit Ads or sponsorship test, and where the sample is too thin to guide one. This is a research aid, not a media inventory or audience measurement product.

## Who, why, decision

For a marketer with a candidate subreddit list and a defined topic/target market. It outputs the sampled posts and their observed counters as evidence; a human decides which venues merit a small test. It never extracts authors as prospects and does not estimate reach, ad inventory, or representativeness.

## Workflow

1. Set topic and target market, then prepare explicit subreddit URLs.
2. Review the collection plan with `--dry-run`; live collection is explicitly opt-in.
3. Inspect the bounded public post sample, evidence URLs, and sample-size flag.
4. Decide whether to test, collect more evidence, or stop; validate any media opportunity directly with Reddit or the publisher.

## Synthetic example -> decision

The bundled synthetic corpus includes three analytics-matching posts in `r/saas`, one matching post in `r/startups`, and unrelated posts elsewhere. Run `python3 tool.py --sample --topic "analytics for early-stage teams"`. The report scores each subreddit separately: `r/saas` may be a `pilot_candidate`, while `r/startups` remains `insufficient_sample`. A one-record per-subreddit corpus is insufficient regardless of other subreddits' sample sizes.

## Quick start

```bash
python3 tool.py --sample --topic "analytics for early-stage teams"
python3 tool.py sample_posts.json planner.json --topic "analytics" 
python3 -m pytest -q
```

For live collection, create a CSV with `subreddit_url` (at most 20 URLs per synchronous request), set `BRIGHT_DATA_API_KEY`, inspect the bounded plan, then explicitly opt in:

```bash
python3 tool.py candidate_subreddits.csv --live --dry-run --topic "analytics for early-stage teams"
python3 tool.py candidate_subreddits.csv planner.json --live --topic "analytics"
```

## Bright Data integration

The current [Reddit Scraper API docs](https://docs.brightdata.com/products/scrapers/reddit/introduction) document Posts dataset `gd_lvz8ah06191smkebj4`, subreddit URL discovery via `type=discover_new&discover_by=subreddit_url`, and `limit_per_input` in the body. Discovery is asynchronous, so live mode uses the documented [`/trigger` → progress → snapshot flow](https://docs.brightdata.com/products/scrapers/scrapers-library/async-requests). It triggers one job for at most 20 subreddits, caps each at 10 returned posts, polls progress at most 60 times at 10-second intervals, then downloads JSON. The billable POST is never retried; a 202 without a valid snapshot ID, malformed responses, failed status, or poll timeout returns a structured error. Collection may incur charges; review current [pricing](https://brightdata.com/pricing/web-scraper) and account access first. CI and offline examples make no live requests.

## Output and limitations

JSON includes per-subreddit sample counts, a 0-100 evidence triage score, decision, source URL/title/subreddit, matched topic terms, observed upvotes/comments, and limitations. The score is not a performance probability: it adds up to 60 points for topic-matching post count (capped at three) and up to 40 points for the share of matching posts with at least one observed comment. A post matches if its title, description, or body contains a whole-word match for at least one topic term longer than two characters. It is a transparent keyword heuristic, not semantic relevance; it may miss synonyms and match incidental mentions. A public-post sample is not representative of community members or target markets; counters do not show ads availability or sponsorship inventory.

## Differentiation

Unlike `bright-data-reddit-outreach` or `hand-raisers`, this does not discover people asking for products, qualify prospects, extract author data, or draft outreach. Unlike `bright-data-reddit-demand-radar`, it does not cluster broad product pains; its decision is about which user-selected subreddit may merit a small media test.

## Safety and FAQ

Only public subreddit pages explicitly provided by the operator are requested. No login, private communities, author profiling, outreach, or posting. `--live` is required for any billable call; dry-run is local only. Empty/invalid input fails rather than triggering collection. Never commit API keys; credentials are read from the environment.

**Does `pilot_candidate` predict campaign performance?** No. It says only that the subreddit has at least three topic-matching sampled posts and at least one observed comment across them.

**Does the tool estimate ad reach or inventory?** No. Confirm both with Reddit or the publisher.

MIT License. Independent demonstration; not affiliated with or endorsed by Bright Data.
