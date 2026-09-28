"""Evidence-first, bounded Reddit subreddit test planner."""
import argparse, csv, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

SAMPLE = [
    {"url":"https://www.reddit.com/r/saas/comments/a1/ops_tools/", "title":"What tools do you use for SaaS analytics?", "description":"Comparing tools for small teams", "community_name":"saas", "num_upvotes":18, "num_comments":22},
    {"url":"https://www.reddit.com/r/startups/comments/b2/analytics/", "title":"Analytics stack for early startups", "description":"Need recommendations", "community_name":"startups", "num_upvotes":12, "num_comments":16},
    {"url":"https://www.reddit.com/r/marketing/comments/c3/measurement/", "title":"How are teams measuring campaigns?", "description":"Marketing measurement discussion", "community_name":"marketing", "num_upvotes":9, "num_comments":11},
    {"url":"https://www.reddit.com/r/smallbusiness/comments/d4/reporting/", "title":"Monthly reporting workflow", "description":"Small business operator asks about reporting", "community_name":"smallbusiness", "num_upvotes":6, "num_comments":8},
    {"url":"https://www.reddit.com/r/saas/comments/e5/analytics-stack/", "title":"Analytics stack for a bootstrapped SaaS", "description":"Comparing analytics tools", "community_name":"saas", "num_upvotes":8, "num_comments":5},
    {"url":"https://www.reddit.com/r/saas/comments/f6/product-analytics/", "title":"Product analytics recommendations", "description":"What analytics tool fits a small SaaS?", "community_name":"saas", "num_upvotes":11, "num_comments":0},
]

class BrightDataError(Exception):
    def __init__(self, code, message): self.code=code; super().__init__(message)

def analyze(posts, topic, requested_subreddits=None, minimum_per_subreddit=3):
    if not posts: raise ValueError("No posts supplied")
    if not isinstance(topic,str) or not topic.strip(): raise ValueError("A topic/target-market phrase is required")
    terms=[t.lower() for t in re.findall(r"[a-z0-9]+",topic) if len(t)>2]
    if not terms: raise ValueError("Topic must contain at least one meaningful word")
    grouped={name:[] for name in (requested_subreddits or [])}
    for p in posts:
        sub=p.get("community_name") or p.get("subreddit")
        if not isinstance(sub,str) or not sub.strip(): raise ValueError("Every post must include a subreddit")
        grouped.setdefault(sub,[]).append(p)
    scored={}; all_evidence=[]
    for subreddit, records in sorted(grouped.items()):
        relevant=[]
        for p in records:
            text=" ".join(str(p.get(k,"")) for k in ("title","description","body")).lower()
            matched=[t for t in terms if re.search(r"\b"+re.escape(t)+r"\b",text)]
            if matched:
                relevant.append(p)
                all_evidence.append({"url":p.get("url",""),"title":p.get("title",""),"subreddit":subreddit,"matched_topic_terms":matched,"observed_comments":p.get("num_comments"),"observed_upvotes":p.get("num_upvotes")})
        discussions=sum(1 for p in relevant if int(p.get("num_comments") or 0)>0)
        comments=sum(int(p.get("num_comments") or 0) for p in relevant)
        decision="insufficient_sample" if len(relevant)<minimum_per_subreddit else ("pilot_candidate" if comments>0 else "insufficient_signal")
        sample_component=min(60.0,60.0*len(relevant)/minimum_per_subreddit)
        discussion_component=40.0*discussions/len(relevant) if relevant else 0.0
        scored[subreddit]={"evidence_score":round(sample_component+discussion_component),"sample_size":len(records),"relevant_sample_size":len(relevant),"discussion_posts":discussions,"observed_comments_in_relevant_sample":comments,"decision":decision}
    return {"topic":topic.strip(),"subreddits":scored,"evidence":all_evidence,"heuristic":{"minimum_relevant_posts_per_subreddit":minimum_per_subreddit,"topic_matching":"A supplied post counts only when its title, description, or body contains a whole-word match for at least one topic term longer than two characters.","evidence_score":"0-100 triage score, not performance probability: up to 60 points for relevant-post sample size capped at the minimum (3), plus up to 40 points for the share of relevant posts with at least one observed comment.","pilot_candidate":"At least the minimum number of topic-matching posts in that subreddit and at least one observed comment across them.","insufficient_signal":"Minimum matched-post sample reached but no observed comments among matching posts."},"limits":["Each subreddit is scored independently; no cross-subreddit overall threshold is used.","This keyword heuristic is not semantic relevance and may miss synonyms or match incidental mentions.","Evidence score is a triage convenience, not campaign outcome, audience size, or reach prediction.","Not representative of subreddit membership or market demand.","Observed counters do not estimate ad reach, inventory, or sponsorship availability.","No authors or members are extracted as prospects."]}

def api_json(url, key, method="GET", body=None):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(url,data=data,headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method=method)
    try:
        with urllib.request.urlopen(req,timeout=75) as response:
            raw=response.read().decode()
            status=response.status
    except urllib.error.HTTPError as e:
        raise BrightDataError("http_error",f"Bright Data returned HTTP {e.code}") from e
    try: result=json.loads(raw)
    except json.JSONDecodeError as e: raise BrightDataError("invalid_response","Bright Data response was not valid JSON") from e
    return status,result

def collect(urls, key, poll_interval=10, max_polls=60):
    if not 1 <= len(urls) <= 20: raise ValueError("Sync collection accepts 1-20 subreddit URLs")
    if any(not isinstance(u,str) for u in urls): raise ValueError("Subreddit URLs must be strings")
    if len(set(urls))!=len(urls): raise ValueError("Subreddit URL inputs must be unique to avoid duplicate billable records")
    if any(not re.fullmatch(r"https://www\.reddit\.com/r/[A-Za-z0-9_]+/?",u) for u in urls): raise ValueError("Each input must be a canonical public subreddit URL")
    if not isinstance(key,str) or not key: raise ValueError("Bright Data API key is required")
    if not 1<=max_polls<=60 or poll_interval<0: raise ValueError("Polling must be bounded to 1-60 polls with a nonnegative interval")
    body={"input":[{"url":u} for u in urls],"limit_per_input":10}
    query=urllib.parse.urlencode({"dataset_id":"gd_lvz8ah06191smkebj4","type":"discover_new","discover_by":"subreddit_url","format":"json"})
    _,trigger=api_json("https://api.brightdata.com/datasets/v3/trigger?"+query,key,"POST",body)
    snapshot_id=trigger.get("snapshot_id") if isinstance(trigger,dict) else None
    if not isinstance(snapshot_id,str) or not re.fullmatch(r"[A-Za-z0-9_-]+",snapshot_id): raise BrightDataError("missing_snapshot_id","Bright Data trigger response did not contain a valid snapshot_id")
    progress_url="https://api.brightdata.com/datasets/v3/progress/"+snapshot_id
    ready=False
    for attempt in range(max_polls):
        _,progress=api_json(progress_url,key)
        if not isinstance(progress,dict) or not isinstance(progress.get("status"),str): raise BrightDataError("invalid_progress","Bright Data progress response lacked a status")
        status=progress["status"]
        if status=="ready": ready=True; break
        if status in ("failed","canceled"): raise BrightDataError("snapshot_"+status,"Bright Data subreddit discovery did not complete successfully")
        if status not in ("starting","running"): raise BrightDataError("invalid_progress","Bright Data returned an unknown snapshot status")
        if attempt+1<max_polls and poll_interval: time.sleep(poll_interval)
    if not ready: raise BrightDataError("poll_timeout","Bright Data snapshot was not ready within the bounded polling window")
    snapshot_url="https://api.brightdata.com/datasets/v3/snapshot/"+snapshot_id+"?format=json"
    _,records=api_json(snapshot_url,key)
    if not isinstance(records,list) or any(not isinstance(row,dict) or not isinstance(row.get("url"),str) for row in records): raise BrightDataError("invalid_response","Bright Data snapshot did not contain an array of post records with URLs")
    return records

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("input",nargs="?"); p.add_argument("output",nargs="?",default="planner.json"); p.add_argument("--sample",action="store_true"); p.add_argument("--live",action="store_true"); p.add_argument("--dry-run",action="store_true"); p.add_argument("--topic",default="")
    a=p.parse_args(argv)
    try:
        if a.sample and a.live: raise ValueError("--sample is offline-only and cannot be combined with --live")
        if a.sample: posts=SAMPLE
        elif a.live:
            if not a.input: raise ValueError("Live mode requires CSV with subreddit_url column")
            if not a.topic: raise ValueError("--topic is required")
            with open(a.input,newline="",encoding="utf-8") as f: urls=[r.get("subreddit_url","").strip() for r in csv.DictReader(f)]
            if not 1<=len(urls)<=20 or len(set(urls))!=len(urls) or any(not re.fullmatch(r"https://www\.reddit\.com/r/[A-Za-z0-9_]+/?",u) for u in urls): raise ValueError("CSV must contain 1-20 unique valid subreddit_url values")
            if a.dry_run: print(json.dumps({"live":True,"url_count":len(urls),"max_posts_per_url":10,"max_status_polls":60,"dataset_id":"gd_lvz8ah06191smkebj4","topic":a.topic})); return 0
            key=os.environ.get("BRIGHT_DATA_API_KEY")
            if not key: raise ValueError("Set BRIGHT_DATA_API_KEY in the environment")
            posts=collect(urls,key)
        elif a.input: posts=json.load(open(a.input,encoding="utf-8"))
        else: p.error("Use --sample or provide JSON input (live requires --live)")
        if a.dry_run:
            print(json.dumps({"live":False,"input_posts":len(posts),"topic":a.topic,"requests":0})); return 0
        requested_subreddits=[re.search(r"/r/([^/]+)/",u).group(1) for u in urls] if a.live else None
        report=analyze(posts,a.topic,requested_subreddits)
        with open(a.output,"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
        print(json.dumps({"output":a.output,"subreddits":len(report["subreddits"]),"pilot_candidates":[name for name,item in report["subreddits"].items() if item["decision"]=="pilot_candidate"]})); return 0
    except BrightDataError as e: print(json.dumps({"error":{"code":e.code,"message":str(e),"retryable":False}}),file=sys.stderr); return 1
    except urllib.error.HTTPError as e: print(json.dumps({"error":{"code":"http_error","message":f"Bright Data returned HTTP {e.code}","retryable":False}}),file=sys.stderr); return 1
    except (ValueError, OSError, urllib.error.URLError, RuntimeError, KeyError) as e: print(json.dumps({"error":{"code":"input_or_transport_error","message":str(e),"retryable":False}}),file=sys.stderr); return 1

if __name__=="__main__": raise SystemExit(main())
