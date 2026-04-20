"""
標高補正機能のテスト

Péronnet et al. (1991) に基づく補正式を検証します。
"""

import pytest
from lib.altitude_adjustment import (
    adjust_marathon_time,
    get_delay_minutes,
    get_altitude_warning,
    ALTITUDE_THRESHOLD_M,
)


class TestAdjustMarathonTime:
    """adjust_marathon_time() のテスト"""

    def test_no_adjustment_at_sea_level(self):
        """海面水準では補正なし"""
        assert adjust_marathon_time(180, 0) == 180.0

    def test_no_adjustment_below_threshold(self):
        """ALTITUDE_THRESHOLD_M 未満では補正なし（東京・大阪等の低地コース）"""
        result = adjust_marathon_time(180, ALTITUDE_THRESHOLD_M - 1)
        assert result == 180.0

    def test_adjustment_at_threshold(self):
        """閾値ちょうどでは補正が発生しない（未満条件）"""
        result = adjust_marathon_time(180, ALTITUDE_THRESHOLD_M)
        assert result == 180.0

    def test_adjustment_above_threshold(self):
        """閾値を超えるとタイムが増加する（501m = 補正発生）"""
        result = adjust_marathon_time(180, ALTITUDE_THRESHOLD_M + 1)
        assert result > 180.0

    def test_adjustment_at_1000m(self):
        """1000m でのタイム補正（Péronnet 式から計算: 約 5.6% 増）"""
        result = adjust_marathon_time(180, 1000)
        # 3:00 → 3:10〜3:12 (±2分の誤差を許容)
        assert 188 <= result <= 194

    def test_adjustment_at_2000m(self):
        """2000m でのタイム補正（Péronnet 式から計算: 約 14% 増）"""
        result = adjust_marathon_time(180, 2000)
        # 3:00 → 3:25〜3:35 の範囲
        assert 205 <= result <= 215

    def test_negative_altitude_returns_base(self):
        """負の標高（死海等）は閾値未満として補正なし"""
        result = adjust_marathon_time(180, -100)
        assert result == 180.0

    def test_monotonic_increase_with_altitude(self):
        """標高が上がるほどタイムも単調増加"""
        t_500 = adjust_marathon_time(180, 500)
        t_1000 = adjust_marathon_time(180, 1000)
        t_2000 = adjust_marathon_time(180, 2000)
        assert t_500 <= t_1000 <= t_2000

    def test_slower_runner_more_affected(self):
        """遅いランナーほど標高の絶対的影響が大きい"""
        delay_fast = get_delay_minutes(150, 2000)  # 2:30
        delay_slow = get_delay_minutes(240, 2000)  # 4:00
        assert delay_slow > delay_fast

    def test_threshold_override_suppresses_correction(self):
        """threshold_m 指定時：平均標高が閾値以下なら補正なし"""
        result = adjust_marathon_time(180, 600, threshold_m=1000)
        assert result == 180.0

    def test_threshold_override_enables_correction(self):
        """threshold_m 指定時：平均標高が閾値超えなら補正あり"""
        result = adjust_marathon_time(180, 600, threshold_m=300)
        assert result > 180.0

    def test_threshold_override_boundary(self):
        """threshold_m 指定時：ちょうど閾値では補正なし（<= 比較の確認）"""
        result = adjust_marathon_time(180, 500, threshold_m=500)
        assert result == 180.0


class TestGetDelayMinutes:
    """get_delay_minutes() のテスト"""

    def test_no_delay_at_sea_level(self):
        """海面水準では遅延ゼロ"""
        assert get_delay_minutes(180, 0) == 0.0

    def test_no_delay_below_threshold(self):
        """閾値未満では遅延ゼロ"""
        assert get_delay_minutes(180, ALTITUDE_THRESHOLD_M - 1) == 0.0

    def test_positive_delay_above_threshold(self):
        """閾値超えで正の遅延"""
        delay = get_delay_minutes(180, 1500)
        assert delay > 0

    def test_delay_is_consistent_with_adjust(self):
        """adjust_marathon_time との一貫性"""
        base = 180.0
        alt = 1000.0
        adjusted = adjust_marathon_time(base, alt)
        delay = get_delay_minutes(base, alt)
        assert abs((adjusted - base) - delay) < 1e-9


class TestGetAltitudeWarning:
    """get_altitude_warning() のテスト"""

    def test_no_warning_low_altitude(self):
        """低地では警告なし"""
        assert get_altitude_warning(300) is None
        assert get_altitude_warning(1000) is None

    def test_warning_at_1500m(self):
        """1500m 以上で高地注意警告"""
        warning = get_altitude_warning(1500)
        assert warning is not None
        assert "高地" in warning

    def test_warning_at_2500m(self):
        """2500m 以上で高高度警告（高山病言及）"""
        warning = get_altitude_warning(2500)
        assert warning is not None
        assert "高山病" in warning or "高高度" in warning
