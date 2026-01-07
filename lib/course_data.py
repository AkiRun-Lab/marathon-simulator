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

    @property
    def distance(self):
        return self.end_km - self.start_km

class CourseData:
    def __init__(self):
        self.segments: List[CourseSegment] = []
    
    @staticmethod
    def get_ehime_marathon_default():
        """
        Returns a simplified model of the Ehime Marathon course.
        Based on user description:
        - 0-7km: Flat/Rolling
        - 7-8km: Hirata Hill (Steep)
        - 10-34km: Coastal (Windy)
        - 36-37km: Hirata Hill (Steep)
        - 37-Finish: Gradual Uphill
        
        Assumed Bearings (APPROXIMATE - needs checking map):
        Ehime Marathon starts in Matsuyama (North-ish) -> Hojo (North) -> Return.
        - Outbound: North/North-East
        - Inbound: South/South-West
        """
        course = CourseData()
        
        # Segment 1: Start to Hirata (0 - 7km)
        # Assuming mostly North bound
        course.segments.append(CourseSegment(0.0, 7.0, 0.0, 10.0, False, "Start Flat"))
        
        # Segment 2: Hirata Hill Outbound (7 - 8km)
        # Steep Uphill
        course.segments.append(CourseSegment(7.0, 8.0, 0.04, 20.0, True, "Hirata Hill (Out)"))
        
        # Segment 3: Descent to Coast (8 - 10km)
        # Downhill
        course.segments.append(CourseSegment(8.0, 10.0, -0.02, 30.0, False, "Descent to Coast"))
        
        # Segment 4: Coastal Outbound (10 - 20km) - Turning point approx 25km? 
        # Actually Ehime turning point is around 25km (Hojo).
        # Let's say 10-25 is North-East bound
        course.segments.append(CourseSegment(10.0, 25.0, 0.0, 45.0, True, "Coastal Outbound (Windy)"))
        
        # Segment 5: Coastal Return (25 - 34km)
        # South-West bound (180 deg turn)
        course.segments.append(CourseSegment(25.0, 34.0, 0.0, 225.0, True, "Coastal Inbound (Windy)"))
        
        # Segment 6: Approach Hirata (34 - 36km)
        course.segments.append(CourseSegment(34.0, 36.0, 0.01, 200.0, False, "Approach Hirata"))
        
        # Segment 7: Hirata Hill Return (36 - 37km)
        # Steep Uphill (User said steep hills at 36km)
        course.segments.append(CourseSegment(36.0, 37.0, 0.04, 200.0, True, "Hirata Hill (Return)"))
        
        # Segment 8: Finish Run (37 - 42.195km)
        # Gradual Uphill
        course.segments.append(CourseSegment(37.0, 42.195, 0.01, 190.0, False, "Gradual Uphill to Goal"))
        
        return course

    def get_segment_at_km(self, current_km) -> Optional[CourseSegment]:
        for seg in self.segments:
            if seg.start_km <= current_km < seg.end_km:
                return seg
        # Handle exact finish line or small floating point overlap
        if len(self.segments) > 0 and current_km >= self.segments[-1].end_km:
             return self.segments[-1]
        return None

    def sample_at_interval_meters(self, interval_m=1000):
        """
        Generate a dataframe of points every `interval_m` meters.
        Optimized for sequential sampling.
        """
        total_dist_km = 42.195
        if self.segments:
            total_dist_km = max(total_dist_km, self.segments[-1].end_km)
            
        points = []
        current_km = 0.0
        
        # Optimization: Keep track of last segment index to avoid full search
        seg_idx = 0
        num_segments = len(self.segments)
        
        while current_km <= total_dist_km + 0.0001: # Include finish
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
                points.append({
                    'km': current_km,
                    'gradient': found_seg.gradient,
                    'bearing': found_seg.bearing_degrees,
                    'wind_exposed': found_seg.is_exposed_to_wind,
                    'segment_name': found_seg.description
                })
            else:
                # Fallback for gaps
                points.append({
                    'km': current_km,
                    'gradient': 0.0,
                    'bearing': 0.0,
                    'wind_exposed': False,
                    'segment_name': "Course Gap (Assumed Flat)"
                })
            
            current_km += (interval_m / 1000.0)
            
        return pd.DataFrame(points)
