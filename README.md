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

The bundled sample contains four invented post records from four candidate subreddits. Run `python3 tool.py --sample --topic "analytics for early-stage teams"`. Output marks this sample `pilot_candidate`, links all four records, and disclaims any reach/inventory claim. That means “worth considering a small, measured test,” not “these communities will deliver buyers.” A one-record input produces `insufficient_sample`.

## Quick start

```bash
python3 tool.py --sample --topic "analytics for early-stage teams"
python3 tool.py sample_posts.json planner.json --topic "analytics" 
python3 -m pytest -q
```

For live collection, create a CSV with `subreddit_url` (at most 20 URLs per synchronous request), set `BRIGHT_DATA_API_KEY`, inspect the bounded plan, then explicitly opt in:

```bash
python3 tool.py candidate_subreddits.csv --live --dry-run
python3 tool.py candidate_subreddits.csv planner.json --live --topic "analytics"
```

## Bright Data integration

The current [Reddit Scraper API docs](https://docs.brightdata.com/products/scrapers/reddit/introduction) document Posts dataset `gd_lvz8ah06191smkebj4`, subreddit URL discovery via `type=discover_new&discover_by=subreddit_url`, and `limit_per_input` in the body. Synchronous requests accept up to 20 URLs; discovery is asynchronous. A `202` snapshot is surfaced as an explicit unsupported async result rather than treated as records. Collection runs may incur charges; review current [pricing](https://brightdata.com/pricing/web-scraper) and account access first. No live request is made in CI or offline examples.

## Output and limitations

JSON includes sample count, decision label, source URL/title/subreddit, observed upvotes/comments, and limitations. The small rule-based decision is a triage heuristic only. A public-post sample is not representative of community members or target markets; Reddit counters do not show ads availability or sponsorship inventory. Results may be incomplete, counters change, and sampled language may not match the intended audience.

## Differentiation

Unlike `bright-data-reddit-outreach` or `hand-raisers`, this does not discover people asking for products, qualify prospects, extract author data, or draft outreach. Unlike `bright-data-reddit-demand-radar`, it does not cluster broad product pains; its decision is about which user-selected subreddit may merit a small media test.

## Safety and FAQ

Only public subreddit pages explicitly provided by the operator are requested. No login, private communities, author profiling, outreach, or posting. `--live` is required for any billable call; dry-run is local only. Empty/invalid input fails rather than triggering collection. Never commit API keys; credentials are read from the environment.

**Does `pilot_candidate` predict campaign performance?** No. It says only that the bounded sample passed a minimal triage threshold.

**Does the tool estimate ad reach or inventory?** No. Confirm both with Reddit or the publisher.

MIT License. Independent demonstration; not affiliated with or endorsed by Bright Data.
