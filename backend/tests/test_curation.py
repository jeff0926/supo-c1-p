from app.schemas import WordTimestamp
from app.services.curation import _chunk_words, _dedupe_overlapping, _parse_response
from app.schemas import ClipCandidate


def test_chunk_words_with_overlap():
    words = [WordTimestamp(word=f"w{i}", start=float(i), end=float(i) + 0.5) for i in range(300)]
    chunks = _chunk_words(words, chunk_seconds=60, overlap_seconds=10)
    assert len(chunks) >= 5
    # overlap means second chunk should start before first ends
    assert chunks[1][0].start < chunks[0][-1].end


def test_parse_response_strips_markdown_fence():
    raw = '```json\n{"clips": [{"title":"a","start_time":0.1,"end_time":10.0,"virality_score":80,"reasoning":"r"}]}\n```'
    result = _parse_response(raw)
    assert len(result.clips) == 1
    assert result.clips[0].title == "a"


def test_dedupe_overlapping_keeps_higher_score():
    clips = [
        ClipCandidate(title="a", start_time=0.0, end_time=10.0, virality_score=80, reasoning="r"),
        ClipCandidate(title="b", start_time=5.0, end_time=15.0, virality_score=90, reasoning="r"),
        ClipCandidate(title="c", start_time=20.0, end_time=30.0, virality_score=70, reasoning="r"),
    ]
    kept = _dedupe_overlapping(clips)
    titles = {c.title for c in kept}
    assert "b" in titles
    assert "c" in titles
    assert "a" not in titles
