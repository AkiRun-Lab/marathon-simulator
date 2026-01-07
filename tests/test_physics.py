import pytest
import numpy as np
from lib.physics import RunningPhysics

class TestRunningPhysics:
    
    def test_minetti_cost_increase_on_uphill(self):
        """Verify energy cost increases on uphill gradients"""
        flat_cost = RunningPhysics.minetti_cost_j_kg_m(0.0)
        uphill_cost = RunningPhysics.minetti_cost_j_kg_m(0.05) # 5% grade
        assert uphill_cost > flat_cost
        
    def test_minetti_cost_decrease_on_gentle_downhill(self):
        """Verify energy cost decreases on gentle downhill (optimal is around -10% to -20%)"""
        flat_cost = RunningPhysics.minetti_cost_j_kg_m(0.0)
        downhill_cost = RunningPhysics.minetti_cost_j_kg_m(-0.05)
        assert downhill_cost < flat_cost

    def test_drag_force_direction(self):
        """Verify drag is positive (cost) when running into wind"""
        # Running 4m/s into 2m/s headwind (wind_speed_parallel = -2)
        # Relative speed 6m/s
        power_headwind = RunningPhysics.calculate_drag_power_watts(4.0, -2.0)
        
        # Running 4m/s with no wind
        power_calm = RunningPhysics.calculate_drag_power_watts(4.0, 0.0)
        
        assert power_headwind > power_calm

    def test_solve_speed_limitations(self):
        """Verify speed decreases with difficulty"""
        mass = 65.0
        vdot = 50 # Approx 2:58 marathon (~4:13/km -> ~3.95 m/s)
        base_speed = RunningPhysics.vdot_to_flat_velocity(vdot)
        base_power = RunningPhysics.calculate_total_power(base_speed, 0.0, 0.0, mass)
        
        # 1. Uphill Speed check
        uphill_speed = RunningPhysics.solve_speed_for_power(base_power, 0.05, 0.0, mass)
        print(f"Base: {base_speed:.2f}, Uphill: {uphill_speed:.2f}")
        assert uphill_speed < base_speed
        
        # 2. Headwind Speed check (5m/s headwind is strong)
        headwind_speed = RunningPhysics.solve_speed_for_power(base_power, 0.0, -5.0, mass)
        print(f"Base: {base_speed:.2f}, Headwind: {headwind_speed:.2f}")
        assert headwind_speed < base_speed

    def test_sanity_check_values(self):
        """Check if values are physically reasonable"""
        # 3 m/s running (~5:33/km)
        # Cost on flat ~ 3.6 - 4.0 J/kg/m
        cost = RunningPhysics.minetti_cost_j_kg_m(0)
        assert 3.5 <= cost <= 4.2
