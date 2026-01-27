"""
気温補正機能のテスト

実装指示書のテストケースを検証します。
"""

import pytest
from lib.temperature_adjustment import (
    adjust_marathon_time,
    format_time,
    get_delay_minutes,
    get_temperature_warning
)


class TestAdjustMarathonTime:
    """adjust_marathon_time() のテスト"""
    
    def test_no_adjustment_at_optimal_temp(self):
        """最適気温(10°C)では調整なし"""
        result = adjust_marathon_time(180, 10)
        assert result == 180
    
    def test_no_adjustment_below_optimal(self):
        """10°C未満では調整なし"""
        result = adjust_marathon_time(180, 5)
        assert result == 180
        
        result = adjust_marathon_time(180, 0)
        assert result == 180
    
    def test_adjustment_at_20c(self):
        """20°Cでの調整値（指示書の早見表と照合）
        
        目標タイム 3:00 @ 20°C → 期待値: 3:09 (約189分)
        """
        result = adjust_marathon_time(180, 20)
        # 許容誤差 ±1分
        assert 188 <= result <= 190
    
    def test_adjustment_at_25c(self):
        """25°Cでの調整値（指示書の早見表と照合）
        
        目標タイム 3:00 @ 25°C → 期待値: 3:13 (約193分)
        """
        result = adjust_marathon_time(180, 25)
        # 許容誤差 ±2分
        assert 191 <= result <= 196
    
    def test_slower_runners_more_affected(self):
        """遅いランナーほど影響が大きい
        
        指数が3.6のため、タイムが長いほど気温の影響が増大する
        """
        fast = adjust_marathon_time(150, 20) - 150  # 2:30
        slow = adjust_marathon_time(240, 20) - 240  # 4:00
        assert slow > fast * 2


class TestFormatTime:
    """format_time() のテスト"""
    
    def test_format_exact_hours(self):
        """整数時間のフォーマット"""
        assert format_time(180) == "3:00:00"
        assert format_time(240) == "4:00:00"
    
    def test_format_with_minutes(self):
        """分を含むフォーマット"""
        assert format_time(189.2) == "3:09:11"  # 0.2*60=12だが、intで切り捨て
        assert format_time(210.5) == "3:30:30"


class TestGetDelayMinutes:
    """get_delay_minutes() のテスト"""
    
    def test_no_delay_at_optimal(self):
        """最適気温では遅延なし"""
        delay = get_delay_minutes(180, 10)
        assert delay == 0
    
    def test_delay_at_20c(self):
        """20°Cでの遅延時間"""
        delay = get_delay_minutes(180, 20)
        # 約9分の遅延
        assert 8 <= delay <= 10


class TestGetTemperatureWarning:
    """get_temperature_warning() のテスト"""
    
    def test_no_warning_below_25c(self):
        """25°C未満では警告なし"""
        assert get_temperature_warning(20) == ""
        assert get_temperature_warning(24) == ""
    
    def test_warning_at_25c(self):
        """25°C以上で高温注意警告"""
        warning = get_temperature_warning(26)
        assert "高温注意" in warning
    
    def test_danger_at_28c(self):
        """28°C以上で危険警告"""
        warning = get_temperature_warning(28)
        assert "危険" in warning
    
    def test_extreme_danger_at_30c(self):
        """30°C以上で極めて危険警告"""
        warning = get_temperature_warning(31)
        assert "レース中止" in warning


# 早見表との照合テスト
class TestLookupTable:
    """実装指示書の早見表との照合"""
    
    @pytest.mark.parametrize("base_time_min,temp,expected_min,tolerance", [
        (150, 20, 154, 1),  # 2:30 @ 20°C → 2:34
        (180, 20, 189, 1),  # 3:00 @ 20°C → 3:09
        (180, 25, 193, 2),  # 3:00 @ 25°C → 3:13 (許容誤差±2分)
        (240, 20, 274, 2),  # 4:00 @ 20°C → 4:34
    ])
    def test_lookup_table_values(self, base_time_min, temp, expected_min, tolerance):
        """早見表の値と照合"""
        result = adjust_marathon_time(base_time_min, temp)
        assert abs(result - expected_min) <= tolerance
