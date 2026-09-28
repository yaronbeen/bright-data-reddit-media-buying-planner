import tool
import json
import urllib.parse


def test_scores_each_subreddit_using_topic_relevance_and_sample_threshold():
    posts = tool.SAMPLE + [dict(tool.SAMPLE[0], url="https://www.reddit.com/r/saas/comments/e5/x")]
    report = tool.analyze(posts, "analytics")
    assert report["topic"] == "analytics"
    assert report["subreddits"]["saas"]["relevant_sample_size"] == 4
    assert report["subreddits"]["saas"]["decision"] == "pilot_candidate"
    assert report["subreddits"]["saas"]["evidence_score"] > report["subreddits"]["startups"]["evidence_score"]
    assert report["subreddits"]["startups"]["decision"] == "insufficient_sample"
    assert report["heuristic"]
    assert "reach" not in report


def test_topic_must_be_in_supplied_post_text_for_sample_to_count():
    post = {"url":"https://www.reddit.com/r/example/comments/x/y", "title":"Unrelated", "description":"No match", "community_name":"example"}
    assert tool.analyze([post, post, post], "analytics")["subreddits"]["example"]["relevant_sample_size"] == 0

def test_async_collection_rejects_more_than_twenty_before_request(monkeypatch):
    monkeypatch.setattr(tool.urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network called")))
    try:
        tool.collect([f"https://www.reddit.com/r/{i}/" for i in range(21)], "secret")
    except ValueError:
        pass
    else:
        assert False, "expected URL cap"
    try: tool.collect(["https://www.reddit.com/r/saas/"]*2,"secret")
    except ValueError: pass
    else: assert False, "duplicate subreddit should be rejected before billing"

def test_collection_rejects_malformed_trigger_and_202_without_snapshot(monkeypatch):
    class Response:
        def __init__(self,status,payload): self.status=status; self.payload=payload
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return self.payload
    responses=iter([Response(200,b"not json"),Response(202,b'{"message":"pending"}')])
    monkeypatch.setattr(tool.urllib.request,"urlopen",lambda *a,**k:next(responses))
    for expected in ("invalid_response","missing_snapshot_id"):
        try: tool.collect(["https://www.reddit.com/r/saas/"],"secret",poll_interval=0)
        except tool.BrightDataError as e: assert e.code==expected
        else: assert False, "trigger response should be rejected"

def test_live_dry_run_needs_no_key_and_makes_no_request(monkeypatch, capsys):
    monkeypatch.delenv("BRIGHT_DATA_API_KEY", raising=False)
    monkeypatch.setattr(tool.urllib.request, "urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network called")))
    assert tool.main(["candidate_subreddits.csv", "--live", "--dry-run", "--topic", "analytics"]) == 0
    assert json.loads(capsys.readouterr().out)["live"] is True

def test_live_request_uses_bounded_documented_subreddit_discovery(monkeypatch):
    captured={}
    class Response:
        def __init__(self,payload): self.payload=payload; self.status=200
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def read(self): return self.payload
    responses=iter([Response(b'{"snapshot_id":"sd_test123"}'),Response(b'{"snapshot_id":"sd_test123","status":"ready"}'),Response(b'[]')])
    def fake_urlopen(req,timeout):
        captured.setdefault("requests",[]).append({"url":req.full_url,"body":json.loads(req.data) if req.data else None,"method":req.get_method(),"auth":req.get_header("Authorization")})
        return next(responses)
    monkeypatch.setattr(tool.urllib.request,"urlopen",fake_urlopen)
    urls=["https://www.reddit.com/r/saas/","https://www.reddit.com/r/startups/"]
    assert tool.collect(urls,"secret",poll_interval=0)==[]
    trigger=captured["requests"][0]
    query=urllib.parse.parse_qs(urllib.parse.urlsplit(trigger["url"]).query)
    assert query["dataset_id"]==["gd_lvz8ah06191smkebj4"]
    assert query["type"]==["discover_new"] and query["discover_by"]==["subreddit_url"]
    assert query["format"]==["json"]
    assert trigger["body"]=={"input":[{"url":u} for u in urls],"limit_per_input":10}
    assert [r["method"] for r in captured["requests"]]==["POST","GET","GET"]
    assert all(r["auth"]=="Bearer secret" for r in captured["requests"])
    assert "progress/sd_test123" in captured["requests"][1]["url"]
    assert "snapshot/sd_test123?format=json" in captured["requests"][2]["url"]
