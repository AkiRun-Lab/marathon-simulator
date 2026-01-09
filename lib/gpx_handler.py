import gpxpy
import pandas as pd
import numpy as np
from lib.course_data import CourseSegment, CourseData

class GPXHandler:
    def __init__(self, gpx_path):
        self.gpx_path = gpx_path
        
    def parse_to_dataframe(self, window_meters=120):
        """
        Parses GPX file and returns a DataFrame with uniformly sampled (5m) data:
        lat, lon, elevation, time, distance_m, gradient, bearing
        
        Args:
            window_meters (int): Smoothing window size in meters. Default 120m.
        """
        with open(self.gpx_path, 'r') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
            
        points = []
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    points.append({
                        'lat': point.latitude,
                        'lon': point.longitude,
                        'ele': point.elevation,
                        'time': point.time
                    })
                    
        df_raw = pd.DataFrame(points)
        if df_raw.empty:
            return pd.DataFrame()
            
        # --- 1. Calculate Raw Cumulative Distance ---
        raw_lat = df_raw['lat'].values
        raw_lon = df_raw['lon'].values
        raw_ele = df_raw['ele'].values
        
        # Helper: Haversine
        def haversine_vectorized(lat1, lon1, lat2, lon2):
            R = 6371000
            phi1, phi2 = np.radians(lat1), np.radians(lat2)
            dphi = np.radians(lat2 - lat1)
            dlambda = np.radians(lon2 - lon1)
            a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2) * np.sin(dlambda/2)**2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
            return R * c

        # Shift arrays to calc dist between i and i-1
        dists = haversine_vectorized(
            raw_lat[:-1], raw_lon[:-1],
            raw_lat[1:], raw_lon[1:]
        )
        # Cumulative distance starting at 0
        raw_cum_dist = np.concatenate(([0], np.cumsum(dists)))
        
        # --- 1.5. Distance Normalization to 42.195km ---
        total_raw_dist = raw_cum_dist[-1]
        scale_factor = 1.0
        if total_raw_dist > 40000:
             scale_factor = 42195.0 / total_raw_dist
             raw_cum_dist = raw_cum_dist * scale_factor
        
        # --- 2. Resample to Uniform 5m Grid (Linear Interpolation) ---
        target_dist_arr = np.arange(0, raw_cum_dist[-1], 5.0) # 0, 5, 10, ...
        
        # Interpolate Lat, Lon, Ele onto new grid
        interp_lat = np.interp(target_dist_arr, raw_cum_dist, raw_lat)
        interp_lon = np.interp(target_dist_arr, raw_cum_dist, raw_lon)
        interp_ele = np.interp(target_dist_arr, raw_cum_dist, raw_ele)
        
        df_resampled = pd.DataFrame({
            'distance_m': target_dist_arr,
            'lat': interp_lat,
            'lon': interp_lon,
            'ele': interp_ele
        })
        
        # --- 3. Calculate Bearing on Resampled Data ---
        # Bearing between point i and i+1
        # Formula from https://www.movable-type.co.uk/scripts/latlong.html
        def calc_bearing_vec(lat1, lon1, lat2, lon2):
            y = np.sin(np.radians(lon2-lon1)) * np.cos(np.radians(lat2))
            x = np.cos(np.radians(lat1)) * np.sin(np.radians(lat2)) - \
                np.sin(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.cos(np.radians(lon2-lon1))
            theta = np.arctan2(y, x)
            return (np.degrees(theta) + 360) % 360

        bearings = calc_bearing_vec(
            df_resampled['lat'].values[:-1], df_resampled['lon'].values[:-1],
            df_resampled['lat'].values[1:], df_resampled['lon'].values[1:]
        )
        # Append last bearing to keep length same
        bearings = np.concatenate((bearings, [bearings[-1]]))
        df_resampled['bearing'] = bearings

        # --- 4. Elevation Smoothing (Distance based) ---
        # Data is now strictly 5m spaced. 
        # Calculate window size from meters. Ensure odd number.
        window_size = int(window_meters / 5)
        if window_size < 1: window_size = 1
        if window_size % 2 == 0: window_size += 1
        
        df_resampled['ele_smooth'] = df_resampled['ele'].rolling(window=window_size, center=True, min_periods=1).mean()
        
        # --- 5. Gradient Calculation with Thresholding ---
        # Calculate diff first
        ele_diff = df_resampled['ele_smooth'].diff().fillna(0)
        
        # Threshold: ignore changes smaller than 0cm (no threshold)
        # User requested 0 filtering. Smoothing window takes care of noise.
        # ele_diff[ele_diff.abs() < 0.0] = 0 # Disabled
        
        # Calculate Gradient from filtered diff
        df_resampled['gradient'] = ele_diff / 5.0
        
        # Clip crazy gradients
        df_resampled['gradient'] = df_resampled['gradient'].clip(-0.2, 0.2)
        
        # Smooth Gradient again using the same window
        df_resampled['gradient'] = df_resampled['gradient'].rolling(window=window_size, center=True, min_periods=1).mean()
        
        return df_resampled

    def to_course_data(self, smoothing_window_m=120) -> CourseData:
        """
        Convert to CourseData.
        Input dataframe is already 5m resampled, so we can iterate directly.
        """
        df = self.parse_to_dataframe(window_meters=smoothing_window_m)
        course = CourseData()
        
        if df.empty:
            return course

        # Iterate over uniform 5m points
        # Using itertuples for speed
        total_rows = len(df)
        
        for i, row in enumerate(df.itertuples()):
            # row: Index, distance_m, lat, lon, ele, bearing, ele_smooth, gradient
            
            start_km = row.distance_m / 1000.0
            
            if i < total_rows - 1:
                end_km = df.iloc[i+1]['distance_m'] / 1000.0
            else:
                end_km = start_km + 0.005 # +5m
                
            # Description
            desc = ""
            if 7.0 <= start_km <= 8.0: desc = "平田の坂 (往路)"
            elif 36.0 <= start_km <= 37.0: desc = "平田の坂 (復路)"
            elif 10.0 <= start_km <= 34.0: desc = "海岸線"
            
            segment = CourseSegment(
                start_km=start_km,
                end_km=end_km,
                gradient=row.gradient,
                bearing_degrees=row.bearing,
                is_exposed_to_wind=True,
                description=desc,
                start_lat=row.lat,
                start_lon=row.lon
            )
            course.segments.append(segment)
            
        return course
