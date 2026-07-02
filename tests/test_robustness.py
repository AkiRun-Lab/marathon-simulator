"""コードレビュー（2026-07-03）フェーズ2で追加した堅牢化のテスト

- Y-1: PacingStrategy の target_time_sec 判定（0 や None のフォールバック）
- Y-2: 急勾配×低い坂道強度でもタイムが崩壊しない（9999秒廃止・乗数クランプ）
- Y-3: 標高タグのないGPXの検証
"""
import os
import tempfile

import pytest

from lib.course_data import CourseData, CourseSegment
from lib.pacing_strategy import PacingStrategy
from lib.gpx_handler import GPXHandler


class TestPacingStrategyRobustness:

    def test_zero_target_time_falls_back_to_default(self):
        """target_time_sec=0 はゼロ除算せず4時間フォールバックになる"""
        strategy = PacingStrategy(target_time_sec=0)
        assert strategy.base_speed_ms == pytest.approx(42195.0 / (4 * 3600))

    def test_none_target_time_falls_back_to_default(self):
        strategy = PacingStrategy(target_time_sec=None)
        assert strategy.base_speed_ms == pytest.approx(42195.0 / (4 * 3600))

    def test_steep_course_with_low_hill_preference_no_time_explosion(self):
        """急勾配20%×坂道強度70%でも 5m区間に9999秒が入らない"""
        course = CourseData()
        course.segments.append(CourseSegment(0.0, 2.0, 0.2, 0.0, False, "Steep"))
        course.segments.append(CourseSegment(2.0, 42.195, 0.0, 0.0, False, "Flat"))

        strategy = PacingStrategy(
            mass_kg=60.0,
            target_time_sec=3.5 * 3600,
            hill_preference=70,
            pacing_preference="even",
        )
        df = strategy.generate_pace_table(course, interval_meters=5)

        # 旧実装では9999秒/5mが混入した。最悪でも下限速度0.1m/s→50秒/5m
        assert df['time_sec'].max() <= 50.0 + 1e-6
        assert (df['speed_ms'] > 0).all()
        # 合計タイムが非現実的な値（数十時間）に崩壊していない
        assert df['time_sec'].sum() < 12 * 3600


class TestSamplingDistance:

    def test_total_sampled_distance_is_exactly_42_195(self):
        """終点にも5m区間を加算して42.200km扱いになる過大計上がない（G-7）"""
        course = CourseData()
        course.segments.append(CourseSegment(0.0, 42.195, 0.0, 0.0, False, "Flat"))
        df = course.sample_at_interval_meters(5)
        assert len(df) == 8439  # 42195m / 5m
        assert df['km'].iloc[-1] == pytest.approx(42.190)


class TestGPXElevationValidation:

    def _write_gpx(self, trkpts: str) -> str:
        content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">\n'
            f'<trk><trkseg>{trkpts}</trkseg></trk></gpx>\n'
        )
        fd, path = tempfile.mkstemp(suffix=".gpx")
        with os.fdopen(fd, "w") as f:
            f.write(content)
        return path

    def test_gpx_without_elevation_raises_value_error(self):
        """<ele> なしのGPXは明示的な ValueError（旧実装はTypeErrorクラッシュ）"""
        pts = "".join(
            f'<trkpt lat="{35.0 + i * 0.001}" lon="139.0"></trkpt>' for i in range(10)
        )
        path = self._write_gpx(pts)
        try:
            with pytest.raises(ValueError, match="標高データ"):
                GPXHandler(path).parse_to_dataframe()
        finally:
            os.remove(path)

    def test_gpx_with_partial_elevation_interpolates(self):
        """一部欠損の <ele> は補間されて正常にパースできる"""
        pts = []
        for i in range(10):
            ele = f"<ele>{10 + i}</ele>" if i % 2 == 0 else ""
            pts.append(f'<trkpt lat="{35.0 + i * 0.001}" lon="139.0">{ele}</trkpt>')
        path = self._write_gpx("".join(pts))
        try:
            df = GPXHandler(path).parse_to_dataframe()
            assert not df.empty
            assert df['ele'].notnull().all()
        finally:
            os.remove(path)
