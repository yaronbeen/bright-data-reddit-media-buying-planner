import tool


def test_recommends_only_from_bounded_sample_and_keeps_evidence():
    report = tool.analyze(tool.SAMPLE)
    assert report["decision"] == "pilot_candidate"
    assert report["sample_size"] == 4
    assert report["evidence"][0]["url"].startswith("https://www.reddit.com/")
    assert "reach" not in report


def test_small_sample_is_inconclusive():
    report = tool.analyze(tool.SAMPLE[:1])
    assert report["decision"] == "insufficient_sample"
