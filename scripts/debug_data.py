import pandas as pd
from lib.vdot_handler import VDOTHandler
from lib.gpx_handler import GPXHandler
from lib.course_data import CourseData
import os

def debug_vdot():
    print("--- Debugging VDOT Handler ---")
    if not os.path.exists("data/VDOT一覧表.csv"):
        print("VDOT file not found!")
        return
        
    vdot = VDOTHandler("data/VDOT一覧表.csv")
    print(f"Detected Marathon Column: {vdot.marathon_col}")
    print(f"Columns in CSV: {vdot.vdot_df.columns.tolist()}")
    
    target = "3:00:00"
    closest = vdot.get_closest_vdot(target)
    time_for_closest = vdot.get_time_for_vdot(closest)
    
    print(f"Target: {target}")
    print(f"Closest VDOT: {closest}")
    print(f"Time for that VDOT: {time_for_closest}")
    
    # Check if seconds conversion works
    sec = vdot._time_str_to_seconds(time_for_closest)
    print(f"Seconds: {sec}")

def debug_gpx():
    print("\n--- Debugging GPX Handler ---")
    if not os.path.exists("data/Ehime-marathon2025.gpx"):
        print("GPX file not found!")
        return

    handler = GPXHandler("data/Ehime-marathon2025.gpx")
    df = handler.parse_to_dataframe()
    print(f"Total Points: {len(df)}")
    print(f"Total Distance (m): {df['distance_m'].max()}")
    
    course = handler.to_course_data()
    print(f"Course Segments generated: {len(course.segments)}")
    if course.segments:
        print(f"Last Segment End (km): {course.segments[-1].end_km}")

if __name__ == "__main__":
    debug_vdot()
    debug_gpx()
