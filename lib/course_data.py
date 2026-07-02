import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class CourseSegment:
    start_km: float
    end_km: float
    gradient: float # Decimal (0.01 = 1%)
    bearing_degrees: float # 0=North, 90=East
    is_exposed_to_wind: bool = False
    description: str = ""
    start_lat: Optional[float] = None
    start_lon: Optional[float] = None
    start_elevation: Optional[float] = None  # 絶対標高（海抜 m）、GPX の ele_smooth から取得

    @property
    def distance(self):
        return self.end_km - self.start_km

class CourseData:
    def __init__(self):
        self.segments: List[CourseSegment] = []

    def sample_at_interval_meters(self, interval_m=1000):
        """
        Generate a dataframe of points every `interval_m` meters.
        Optimized for sequential sampling.
        """
        total_dist_km = 42.195
        if self.segments:
            total_dist_km = max(total_dist_km, self.segments[-1].end_km)
            
        points = []

        # Optimization: Keep track of last segment index to avoid full search
        seg_idx = 0
        num_segments = len(self.segments)

        # 各ポイントは [current_km, current_km + interval) の区間の始点を表す。
        # 終点そのもの（42.195km地点）を含めると1区間ぶん距離を過大計上するため含めない。
        n_points = int(round(total_dist_km * 1000.0 / interval_m))
        for point_idx in range(n_points):
            current_km = point_idx * interval_m / 1000.0
            # Find segment efficiently (assuming sequential access)
            found_seg = None
            if num_segments > 0:
                # Check current cached index
                if self.segments[seg_idx].start_km <= current_km:
                     # Move forward if needed
                     while seg_idx < num_segments - 1 and self.segments[seg_idx].end_km <= current_km:
                         seg_idx += 1
                     
                     if self.segments[seg_idx].start_km <= current_km < self.segments[seg_idx].end_km:
                         found_seg = self.segments[seg_idx]
                     elif current_km >= self.segments[-1].end_km: # Handle finish line
                         found_seg = self.segments[-1]
                
                # If still not found (e.g. gaps), linear search or just None
                # But our logic assumes contiguous segments usually.
            
            # Handling Gaps:
            # If GPX has gaps (e.g. tunnel), found_seg might be None.
            # We MUST NOT skip this point, otherwise the runner teleports.
            # We assume flat terrain for gaps.
            if found_seg:
                lat = found_seg.start_lat
                lon = found_seg.start_lon
                
                points.append({
                    'km': current_km,
                    'gradient': found_seg.gradient,
                    'bearing': found_seg.bearing_degrees,
                    'wind_exposed': found_seg.is_exposed_to_wind,
                    'segment_name': found_seg.description,
                    'lat': lat,
                    'lon': lon
                })
            else:
                # Fallback for gaps
                points.append({
                    'km': current_km,
                    'gradient': 0.0,
                    'bearing': 0.0,
                    'wind_exposed': False,
                    'segment_name': "Course Gap (Assumed Flat)",
                    'lat': None,
                    'lon': None
                })

        return pd.DataFrame(points)

    def calculate_mean_elevation(self) -> float:
        """コース全体の距離加重平均標高（海抜 m）を返す

        CourseSegment.start_elevation が None のセグメントは除外する。
        全セグメントが None の場合（海抜データなし）は 0.0 を返す。
        """
        total_dist = 0.0
        weighted_sum = 0.0
        for seg in self.segments:
            if seg.start_elevation is not None:
                dist = seg.end_km - seg.start_km
                weighted_sum += seg.start_elevation * dist
                total_dist += dist
        return weighted_sum / total_dist if total_dist > 0 else 0.0

    def calculate_elevation_gain(self) -> float:
        """
        Calculate total elevation gain (sum of positive vertical rise).
        Using simple gradient * distance integration.
        """
        total_gain = 0.0
        for seg in self.segments:
             rise = seg.gradient * (seg.end_km - seg.start_km) * 1000.0 # m
             if rise > 0:
                 total_gain += rise
        return total_gain

