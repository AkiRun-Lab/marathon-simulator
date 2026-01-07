import gpxpy
import pandas as pd
import numpy as np
from lib.course_data import CourseSegment, CourseData

class GPXHandler:
    def __init__(self, gpx_path):
        self.gpx_path = gpx_path
        
    def parse_to_dataframe(self):
        """
        Parses GPX file and returns a DataFrame with:
        lat, lon, elevation, time, distance_from_start, gradient, bearing
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
                    
        df = pd.DataFrame(points)
        
        # Calculate distance info
        # Haversine or simple approximation? gpxpy has utility needed?
        # Let's use simple iterative calculation for accuracy on track
        distances = [0.0]
        bearings = [0.0] # Bearing from previous point to current
        
        # Helper for bearing
        def calculate_bearing(lat1, lon1, lat2, lon2):
            # Forward Azimuth
            # Formula from https://www.movable-type.co.uk/scripts/latlong.html
            y = np.sin(np.radians(lon2-lon1)) * np.cos(np.radians(lat2))
            x = np.cos(np.radians(lat1)) * np.sin(np.radians(lat2)) - \
                np.sin(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.cos(np.radians(lon2-lon1))
            theta = np.arctan2(y, x)
            deg = (np.degrees(theta) + 360) % 360
            return deg

        # Helper for distance
        def haversine_distance(lat1, lon1, lat2, lon2):
            R = 6371000 # Earth radius in meters
            phi1, phi2 = np.radians(lat1), np.radians(lat2)
            dphi = np.radians(lat2 - lat1)
            dlambda = np.radians(lon2 - lon1)
            
            a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2) * np.sin(dlambda/2)**2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
            return R * c

        for i in range(1, len(df)):
            lat1, lon1 = df.iloc[i-1]['lat'], df.iloc[i-1]['lon']
            lat2, lon2 = df.iloc[i]['lat'], df.iloc[i]['lon']
            
            dist = haversine_distance(lat1, lon1, lat2, lon2)
            bearing = calculate_bearing(lat1, lon1, lat2, lon2)
            
            distances.append(distances[-1] + dist)
            bearings.append(bearing)
            
        # Distance Normalization:
        # GPS tracks often measure longer (weaving, noise) or shorter.
        # We scale the entire track to match exactly 42.195km.
        # This fixes "short" finish lines in simulation.
        raw_distances = np.array(distances)
        raw_total_dist = raw_distances[-1]
        
        if raw_total_dist > 40000: # Only apply if it looks like a marathon (safety)
            scale_factor = 42195.0 / raw_total_dist
            distances = (raw_distances * scale_factor).tolist()
            # Note: This effectively scales each segment slightly.
            
        df['distance_m'] = distances
        df['bearing'] = bearings
        
        # Adjust bearing: shift by 1 to align bearing TO current point (or FROM prev)
        # It's already FROM prev to current.
        
        # Smoothing Elevation for Gradient
        # Raw GPX elevation is very noisy. Gradient calculation will be erratic.
        # Window rolling average.
        df['ele_smooth'] = df['ele'].rolling(window=10, center=True).mean().fillna(df['ele'])
        
        # Calculate Gradient
        # gradient = d_ele / d_dist
        # Use simple difference over small window to avoid div by zero
        df['gradient'] = df['ele_smooth'].diff() / df['distance_m'].diff()
        df['gradient'] = df['gradient'].fillna(0.0)
        # Clip crazy gradients (e.g. tunnels or gps errors)
        df['gradient'] = df['gradient'].clip(-0.2, 0.2)
        
        # Smooth gradient again
        df['gradient'] = df['gradient'].rolling(window=20, center=True).mean().fillna(0.0)
        
        return df

    def to_course_data(self) -> CourseData:
        """
        Convert parsed GPX dataframe into the app's CourseData structure (Segments).
        Since Physics model works better with segments, we can either:
        1. Create many small segments (e.g. every 100m).
        2. Keep sampled approach.
        
        The app uses 'CourseData.sample_at_interval_meters'.
        We can subclass CourseData to use the DF directly instead of segments list suitable?
        Or just generate 100m segments for the whole race.
        """
        df = self.parse_to_dataframe()
        course = CourseData()
        
        # Split into 5m chunks for high resolution
        total_dist = df['distance_m'].max()
        step = 5
        current_step = 0
        
        while current_step < total_dist:
            end_step = min(current_step + step, total_dist)
            
            # Filter rows in this range
            mask = (df['distance_m'] >= current_step) & (df['distance_m'] < end_step)
            chunk = df[mask]
            
            if chunk.empty:
                current_step += step
                continue
                
            avg_grad = chunk['gradient'].mean()
            if np.isnan(avg_grad): avg_grad = 0.0
            
            avg_bearing = chunk['bearing'].mean() # Vector mean is better but scalar ok for small steps
            
            # Wind Exposure:
            # Simple heuristic: Coastal section (10-34km) AND no obvious blockage?
            # User said 10-34km is coastal.
            # Let's assume km 10 to 34 are exposed.
            km_start = current_step / 1000.0
            is_exposed = (10.0 <= km_start <= 34.0)
            
            # Description
            desc = ""
            if 7.0 <= km_start <= 8.0: desc = "平田の坂 (往路)"
            elif 36.0 <= km_start <= 37.0: desc = "平田の坂 (復路)"
            elif 10.0 <= km_start <= 34.0: desc = "海岸線"
            
            segment = CourseSegment(
                start_km=current_step/1000.0,
                end_km=end_step/1000.0,
                gradient=avg_grad,
                bearing_degrees=avg_bearing,
                is_exposed_to_wind=is_exposed,
                description=desc
            )
            course.segments.append(segment)
            
            current_step += step
            
        return course
