import sys
from pathlib import Path
from types import SimpleNamespace

API_DIR = Path(__file__).resolve().parent.parent.parent / "api-server"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from routers.content import _build_chapter_position_locator


def _chapter(
    *,
    chapter_id: int,
    chapter_number: int,
    title: str,
    start_char: int | None = None,
    end_char: int | None = None,
    content: str = "",
):
    return SimpleNamespace(
        id=chapter_id,
        chapter_number=chapter_number,
        title=title,
        start_char=start_char,
        end_char=end_char,
        content=content,
        position=chapter_number,
    )


def test_locator_uses_explicit_start_and_end_chars():
    locate = _build_chapter_position_locator(
        [
            _chapter(chapter_id=10, chapter_number=1, title="Uno", start_char=0, end_char=100),
            _chapter(chapter_id=20, chapter_number=2, title="Dos", start_char=100, end_char=250),
        ]
    )

    loc = locate(120)

    assert loc == {
        "id": 20,
        "chapter_number": 2,
        "title": "Dos",
        "start_char_in_chapter": 20,
    }


def test_locator_falls_back_to_cumulative_lengths_when_bounds_are_missing():
    locate = _build_chapter_position_locator(
        [
            _chapter(chapter_id=10, chapter_number=1, title="Uno", content="abcd"),
            _chapter(chapter_id=20, chapter_number=2, title="Dos", content="efghij"),
        ]
    )

    loc = locate(6)

    assert loc == {
        "id": 20,
        "chapter_number": 2,
        "title": "Dos",
        "start_char_in_chapter": 2,
    }


def test_locator_returns_none_for_out_of_bounds_offsets():
    locate = _build_chapter_position_locator(
        [_chapter(chapter_id=10, chapter_number=1, title="Uno", start_char=0, end_char=10)]
    )

    assert locate(None) is None
    assert locate(99) is None
