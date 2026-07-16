"""
シューマッチング診断ツールへのURL組み立て（build_shoe_finder_url）のテスト
"""

from lib.shoe_finder import (
    SHOE_FINDER_VDOT_MAX,
    SHOE_FINDER_VDOT_MIN,
    build_shoe_finder_url,
)

BASE_URL = "https://akirun.net/shoe-finder/"


class TestBuildShoeFinderUrl:
    def test_normal_value(self):
        assert build_shoe_finder_url(54, BASE_URL) == f"{BASE_URL}?vdot=54"

    def test_float_rounds_up(self):
        assert build_shoe_finder_url(54.6, BASE_URL) == f"{BASE_URL}?vdot=55"

    def test_float_rounds_down(self):
        assert build_shoe_finder_url(54.4, BASE_URL) == f"{BASE_URL}?vdot=54"

    def test_none_returns_none(self):
        assert build_shoe_finder_url(None, BASE_URL) is None

    def test_non_numeric_returns_none(self):
        assert build_shoe_finder_url("invalid", BASE_URL) is None
        assert build_shoe_finder_url([], BASE_URL) is None

    def test_bool_returns_none(self):
        # bool は int のサブクラスのため明示的に除外する
        assert build_shoe_finder_url(True, BASE_URL) is None
        assert build_shoe_finder_url(False, BASE_URL) is None

    def test_below_min_clamped(self):
        assert build_shoe_finder_url(10, BASE_URL) == f"{BASE_URL}?vdot={SHOE_FINDER_VDOT_MIN}"

    def test_above_max_clamped(self):
        assert build_shoe_finder_url(200, BASE_URL) == f"{BASE_URL}?vdot={SHOE_FINDER_VDOT_MAX}"

    def test_at_boundaries(self):
        assert build_shoe_finder_url(30, BASE_URL) == f"{BASE_URL}?vdot=30"
        assert build_shoe_finder_url(85, BASE_URL) == f"{BASE_URL}?vdot=85"
