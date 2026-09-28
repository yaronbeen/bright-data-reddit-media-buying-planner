"""Evidence-first, bounded Reddit subreddit test planner."""
import argparse, csv, json, os, sys, urllib.error, urllib.parse, urllib.request

SAMPLE = [
    {"url":"https://www.reddit.com/r/saas/comments/a1/ops_tools/", "title":"What tools do you use for SaaS analytics?", "description":"Comparing tools for small teams", "community_name":"saas", "num_upvotes":18, "num_comments":22},
    {"url":"https://www.reddit.com/r/startups/comments/b2/analytics/", "title":"Analytics stack for early startups", "description":"Need recommendations", "community_name":"startups", "num_upvotes":12, "num_comments":16},
    {"url":"https://www.reddit.com/r/marketing/comments/c3/measurement/", "title":"How are teams measuring campaigns?", "description":"Marketing measurement discussion", "community_name":"marketing", "num_upvotes":9, "num_comments":11},
    {"url":"https://www.reddit.com/r/smallbusiness/comments/d4/reporting/", "title":"Monthly reporting workflow", "description":"Small business operator asks about reporting", "community_name":"smallbusiness", "num_upvotes":6, "num_comments":8},
]

def analyze(posts, minimum=3):
    if not posts: raise ValueError("No posts supplied")
    evidence = [{"url":p.get("url", ""), "title":p.get("title", ""), "subreddit":p.get("community_name", ""), "observed_comments":p.get("num_comments"), "observed_upvotes":p.get("num_upvotes")} for p in posts]
    engaged = sum(1 for p in posts if (p.get("num_comments") or 0) > 0)
    return {"sample_size":len(posts), "decision":"insufficient_sample" if len(posts)<minimum else ("pilot_candidate" if engaged >= minimum else "insufficient_signal"), "basis":"A bounded public-post sample only; candidate test venues require human review.", "evidence":evidence, "limits":["Not representative of subreddit membership or market demand.", "Observed counters do not estimate ad reach, inventory, or sponsorship availability.", "No authors or members are extracted as prospects."]}

def collect(urls, key):
    if not 1 <= len(urls) <= 20: raise ValueError("Sync collection accepts 1-20 subreddit URLs")
    body={"input":[{"url":u} for u in urls],"limit_per_input":10}
    query=urllib.parse.urlencode({"dataset_id":"gd_lvz8ah06191smkebj4","type":"discover_new","discover_by":"subreddit_url","limit_per_input":10})
    req=urllib.request.Request("https://api.brightdata.com/datasets/v3/scrape?"+query,data=json.dumps(body).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=75) as response:
        payload=response.read().decode()
        if response.status==202: raise RuntimeError("Bright Data returned async snapshot; use the documented async workflow; no records were treated as returned")
        return json.loads(payload)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("input",nargs="?"); p.add_argument("output",nargs="?",default="planner.json"); p.add_argument("--sample",action="store_true"); p.add_argument("--live",action="store_true"); p.add_argument("--dry-run",action="store_true"); p.add_argument("--topic",default="")
    a=p.parse_args()
    try:
        if a.sample: posts=SAMPLE
        elif a.live:
            if not a.input: raise ValueError("Live mode requires CSV with subreddit_url column")
            with open(a.input,newline="",encoding="utf-8") as f: urls=[r["subreddit_url"] for r in csv.DictReader(f)]
            if a.dry_run: print(json.dumps({"live":True,"url_count":len(urls),"max_posts_per_url":10,"dataset_id":"gd_lvz8ah06191smkebj4"})); return 0
            key=os.environ.get("BRIGHT_DATA_API_KEY")
            if not key: raise ValueError("Set BRIGHT_DATA_API_KEY in the environment")
            posts=collect(urls,key)
        elif a.input: posts=json.load(open(a.input,encoding="utf-8"))
        else: p.error("Use --sample or provide JSON input (live requires --live)")
        report=analyze(posts); report["topic"]=a.topic
        with open(a.output,"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
        print(json.dumps({"output":a.output,"decision":report["decision"],"sample_size":report["sample_size"]})); return 0
    except (ValueError, OSError, urllib.error.URLError, RuntimeError, KeyError) as e: print(str(e),file=sys.stderr); return 1

if __name__=="__main__": raise SystemExit(main())
