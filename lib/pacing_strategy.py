import pandas as pd
import numpy as np
from lib.physics import RunningPhysics
from lib.course_data import CourseData

class PacingStrategy:
    def __init__(self, mass_kg=65.0, vdot=45.0, wind_speed_ms=0.0, wind_dir_degrees=0.0, target_time_sec=None, hill_preference=100.0, pacing_preference="even"):
        """
        hill_preference: Float/Int 70 to 130 (Percentage of flat power on 5% gradient).
        pacing_preference: String "even", "positive", "negative".
        """
        self.mass = mass_kg
        self.vdot = vdot
        self.wind_speed_ms = wind_speed_ms
        self.wind_dir_degrees = wind_dir_degrees
        self.hill_preference = float(hill_preference) # 70.0 - 130.0
        self.pacing_preference = pacing_preference
        
        # Calculate Base Power (Watts)
        if target_time_sec:
            # If target time is provided (from VDOT table), use it to set base speed
            self.base_speed_ms = 42195.0 / target_time_sec
        else:
            # Fallback
            raw_v_max = RunningPhysics.vdot_to_flat_velocity(self.vdot)
            self.base_speed_ms = raw_v_max * 0.82 
            
        self.target_power = RunningPhysics.calculate_total_power(
            velocity=self.base_speed_ms,
            gradient=0.0,
            wind_speed=0.0,
            mass=self.mass
        )
        
    def generate_pace_table(self, course_data: CourseData, interval_meters=1000):
        """
        Generate a point-by-point simulation with variable power distribution.
        """
        # Sample the course
        df = course_data.sample_at_interval_meters(interval_meters)
        
        if df.empty:
            return df
            
        # --- Power Profile Calculation ---
        # 1. Base Multipliers
        km_array = df['km'].values
        grad_array = df['gradient'].values
        total_dist_km = 42.195
        
        # Split Strategy (Linear Ramp)
        # Positive: 1.05 -> 0.95
        # Negative: 0.95 -> 1.05
        split_factors = np.ones(len(df))
        if self.pacing_preference == "positive":
            split_factors = 1.05 - (0.10 * (km_array / total_dist_km))
        elif self.pacing_preference == "negative":
            split_factors = 0.95 + (0.10 * (km_array / total_dist_km))
            
        # Hill Strategy (Gradient based)
        # hill_preference is Power % at 5% gradient. e.g. 120 means 1.2x power at 5% grade.
        # Formula: M = 1 + (gradient * K)
        # At grad=0.05, M = preference/100.
        # 1 + 0.05K = pref/100
        # 0.05K = (pref/100) - 1
        # K = ((pref/100) - 1) / 0.05
        
        ref_gradient = 0.05
        target_ratio = self.hill_preference / 100.0
        k_factor = (target_ratio - 1.0) / ref_gradient
        
        # Apply factor
        # If grad is negative (downhill), and K is positive (Push Uphill mode):
        # M < 1.0 (Rest on downhill). Correct.
        # If grad is negative, and K is negative (Save Uphill mode e.g. 80%):
        # target_ratio < 1 -> K is negative.
        # M = 1 + (neg * neg) = 1 + pos > 1.0 (Push on downhill). Correct.
        
        hill_factors = 1.0 + (grad_array * k_factor)
        
        # Combine
        raw_multipliers = split_factors * hill_factors
        
        # Normalize (Energy Budget Constraint)
        # The mean multiplier must be 1.0 so we use the same total energy as the target_power * duration
        avg_mult = np.mean(raw_multipliers)
        final_multipliers = raw_multipliers / avg_mult
        
        # --- Simulation ---
        results = []
        cumulative_time = 0.0
        
        for i, row in df.iterrows():
            segment_power = self.target_power * final_multipliers[i]
            
            # Wind Calculation
            wind_vector_dir = self.wind_dir_degrees + 180
            wind_rad = np.radians(wind_vector_dir - row['bearing'])
            wind_parallel = self.wind_speed_ms * np.cos(wind_rad)
            effective_wind = wind_parallel if row['wind_exposed'] else 0.0
            
            # Gradient Adjustment (Braking on downhills)
            calc_gradient = row['gradient']
            if calc_gradient < 0:
                calc_gradient = calc_gradient * 0.6
            
            # Solve for speed
            optimal_speed = RunningPhysics.solve_speed_for_power(
                target_power=segment_power,
                gradient=calc_gradient,
                wind_speed=effective_wind,
                mass=self.mass
            )
            
            dist_m = interval_meters
            if optimal_speed > 0.1:
                time_sec = dist_m / optimal_speed
            else:
                time_sec = 9999 # Walking/Stopped
                
            cumulative_time += time_sec
            pace_min_km = (1000.0 / optimal_speed) / 60.0 if optimal_speed > 0.1 else 30.0
            
            results.append({
                'km': row['km'],
                'gradient': row['gradient'],
                'segment_name': row['segment_name'],
                'speed_ms': optimal_speed,
                'pace_min_km': pace_min_km,
                'time_sec': time_sec,
                'cumulative_time_sec': cumulative_time
            })
            
        return pd.DataFrame(results)
