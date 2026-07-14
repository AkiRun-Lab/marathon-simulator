"""
CTAカテゴリ判定（judge_cta_category）のテスト
シミュレーション結果（気温・風・起伏・目標タイム）からAmazonカテゴリ別CTAへの
振り分けロジックを検証します。
"""

from lib.cta_selector import (
    DAILY_TRAINER_MIN_TIME_SEC,
    HEAT_MODERATE_MIN_DELAY,
    HEAT_SEVERE_MIN_DELAY,
    HILLY_MIN_GAIN_M,
    WIND_MIN_SPEED_MS,
    judge_cta_category,
)


class TestHeatSevere:
    """気温補正遅延5分以上は heat_severe（最優先）"""

    def test_just_above_threshold(self):
        assert judge_cta_category(5.1, 0.0, 0.0, 10800) == "heat_severe"

    def test_exactly_at_threshold(self):
        assert judge_cta_category(HEAT_SEVERE_MIN_DELAY, 0.0, 0.0, 10800) == "heat_severe"

    def test_large_delay(self):
        assert judge_cta_category(12.0, 0.0, 0.0, 10800) == "heat_severe"


class TestHeatModerate:
    """気温補正遅延2分以上5分未満は heat_moderate"""

    def test_exactly_at_threshold(self):
        assert judge_cta_category(HEAT_MODERATE_MIN_DELAY, 0.0, 0.0, 10800) == "heat_moderate"

    def test_just_below_severe(self):
        assert judge_cta_category(4.9, 0.0, 0.0, 10800) == "heat_moderate"

    def test_just_above_threshold(self):
        assert judge_cta_category(2.1, 0.0, 0.0, 10800) == "heat_moderate"


class TestWind:
    """気温が閾値未満のとき、風速3.0m/s以上は wind"""

    def test_exactly_at_threshold(self):
        assert judge_cta_category(0.0, WIND_MIN_SPEED_MS, 0.0, 10800) == "wind"

    def test_just_above_threshold(self):
        assert judge_cta_category(0.0, 3.1, 0.0, 10800) == "wind"

    def test_just_below_threshold_falls_through(self):
        # 風速2.9は閾値未満なのでwindにならない（起伏・シューズ判定に進む）
        assert judge_cta_category(0.0, 2.9, 0.0, 10800) != "wind"


class TestHilly:
    """気温・風が閾値未満のとき、獲得標高300m以上は hilly"""

    def test_exactly_at_threshold(self):
        assert judge_cta_category(0.0, 0.0, HILLY_MIN_GAIN_M, 10800) == "hilly"

    def test_just_above_threshold(self):
        assert judge_cta_category(0.0, 0.0, 301.0, 10800) == "hilly"

    def test_just_below_threshold_falls_through(self):
        assert judge_cta_category(0.0, 0.0, 299.0, 10800) != "hilly"


class TestShoesDailyVsRace:
    """気温・風・起伏がすべて閾値未満のとき、目標タイム4時間でシューズ訴求が分岐する"""

    def test_exactly_4h_is_daily(self):
        assert judge_cta_category(0.0, 0.0, 0.0, DAILY_TRAINER_MIN_TIME_SEC) == "shoes_daily"

    def test_just_above_4h_is_daily(self):
        assert judge_cta_category(0.0, 0.0, 0.0, DAILY_TRAINER_MIN_TIME_SEC + 1) == "shoes_daily"

    def test_just_below_4h_is_race(self):
        assert judge_cta_category(0.0, 0.0, 0.0, DAILY_TRAINER_MIN_TIME_SEC - 1) == "shoes_race"

    def test_sub3_is_race(self):
        assert judge_cta_category(0.0, 0.0, 0.0, 3 * 3600) == "shoes_race"


class TestPriorityOrder:
    """複数条件が同時に成立する場合、優先順位どおりに判定されること"""

    def test_heat_severe_wins_over_wind_and_hilly(self):
        # 暑さ大＋強風＋起伏大が同時成立 → heat_severeが勝つ
        assert judge_cta_category(6.0, 8.0, 500.0, 10800) == "heat_severe"

    def test_heat_moderate_wins_over_wind_and_hilly(self):
        assert judge_cta_category(3.0, 8.0, 500.0, 10800) == "heat_moderate"

    def test_wind_wins_over_hilly(self):
        assert judge_cta_category(0.0, 5.0, 500.0, 10800) == "wind"

    def test_hilly_wins_over_shoes(self):
        assert judge_cta_category(0.0, 0.0, 400.0, 20000) == "hilly"


class TestInvalidInput:
    """None・負値・型不正な入力でも例外を投げず、安全なデフォルトカテゴリに倒れること"""

    def test_all_none(self):
        # すべてNone→0扱い。base_time_secも不正のためshoes_raceにフォールバック
        assert judge_cta_category(None, None, None, None) == "shoes_race"

    def test_negative_values_treated_as_zero(self):
        assert judge_cta_category(-5.0, -3.0, -100.0, 10800) == "shoes_race"

    def test_string_values(self):
        assert judge_cta_category("hot", "windy", "hilly", "long") == "shoes_race"

    def test_partial_none(self):
        assert judge_cta_category(None, 5.0, None, 10800) == "wind"

    def test_invalid_base_time_sec_falls_back_to_shoes_race(self):
        assert judge_cta_category(0.0, 0.0, 0.0, None) == "shoes_race"
        assert judge_cta_category(0.0, 0.0, 0.0, "invalid") == "shoes_race"

    def test_bool_not_treated_as_number(self):
        # bool は int のサブクラスだが、意図しない誤入力として弾く
        assert judge_cta_category(True, False, False, 10800) == "shoes_race"


class TestReturnsString:
    """戻り値は必ず既知のカテゴリ文字列のいずれかであること"""

    KNOWN_CATEGORIES = {
        "heat_severe",
        "heat_moderate",
        "wind",
        "hilly",
        "shoes_daily",
        "shoes_race",
    }

    def test_various_inputs_return_known_category(self):
        cases = [
            (0.0, 0.0, 0.0, 3600),
            (10.0, 10.0, 1000.0, 20000),
            (None, None, None, None),
            (-1.0, -1.0, -1.0, -1),
        ]
        for args in cases:
            assert judge_cta_category(*args) in self.KNOWN_CATEGORIES
