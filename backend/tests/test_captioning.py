from pathlib import Path

from app.schemas import WordTimestamp
from app.services.captioning import _group_into_phrases, build_ass


def test_group_phrases_splits_on_long_gap():
    words = [
        WordTimestamp(word="hello", start=0.0, end=0.4),
        WordTimestamp(word="world", start=0.5, end=0.9),
        WordTimestamp(word="again", start=2.0, end=2.4),  # >0.6s gap
    ]
    phrases = _group_into_phrases(words)
    assert len(phrases) == 2
    assert phrases[0][0].word == "hello"
    assert phrases[1][0].word == "again"


def test_group_phrases_respects_char_limit():
    words = [WordTimestamp(word="aaaaa", start=i * 0.1, end=i * 0.1 + 0.05) for i in range(20)]
    phrases = _group_into_phrases(words, max_chars=12)
    assert len(phrases) > 1


def test_build_ass_writes_valid_header(tmp_path: Path):
    words = [
        WordTimestamp(word="welcome", start=0.0, end=0.3),
        WordTimestamp(word="to", start=0.31, end=0.5),
        WordTimestamp(word="omniclip", start=0.51, end=1.0),
    ]
    out = tmp_path / "captions.ass"
    build_ass(words, clip_start=0.0, clip_end=1.0, output_path=out)
    text = out.read_text(encoding="utf-8")
    assert "[Script Info]" in text
    assert "[V4+ Styles]" in text
    assert "[Events]" in text
    assert "WELCOME" in text
