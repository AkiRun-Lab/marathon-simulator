import numpy as np
from scipy.optimize import brentq

class RunningPhysics:
    """
    Running physics calculator based on Minetti's metabolic cost comparison
    and aerodynamic drag forces.
    """
    
    # Constants
    GRAVITY = 9.81  # m/s^2
    RHO_AIR = 1.225  # kg/m^3 (Sea level standard)
    DRAG_COEFF = 0.9 # Cd for a runner (approx)
    # Energy efficiency of converting metabolic energy to mechanical work (approx 25%)
    # However, Minetti's cost is already metabolic J/kg/m.
    # We will work primarily in Metabolic Power (Watts/kg) or Cost (J/kg/m).
    
    @staticmethod
    def minetti_cost_j_kg_m(gradient_decimal):
        """
        Calculate metabolic energy cost (J/kg/m) based on gradient.
        Source: Minetti et al. (2002)
        Equation: Cr = 155.4*i^5 - 30.4*i^4 - 43.3*i^3 + 46.3*i^2 + 19.5*i + 3.6
        where i is gradient (rise/run).
        
        Note: The constant 3.6 J/kg/m represents running on flat terrain without air resistance 
        (measurements usually done on treadmill).
        """
        i = gradient_decimal
        cost = (155.4 * i**5) - (30.4 * i**4) - (43.3 * i**3) + \
               (46.3 * i**2) + (19.5 * i) + 3.6
        return cost

    @staticmethod
    def calculate_drag_power_watts(velocity, wind_velocity_parallel, frontal_area=0.4):
        """
        Calculate the MECHANICAL power required to overcome air resistance.
        Force = 0.5 * rho * Cd * A * (v_run - v_wind)^2 
        *Direction matters*: (v_run - v_wind) is the relative air speed.
        If v_run = 3 m/s, v_wind = -2 m/s (headwind), relative = 5 m/s.
        Force aligns with relative velocity.
        Power = Force * velocity_ground
        
        velocity: Ground speed (m/s)
        wind_velocity_parallel: Wind speed component parallel to motion (m/s). 
                                Positive = Tailwind, Negative = Headwind.
        frontal_area: m^2 (Default approx 0.4 - 0.5 for adult)
        
        Returns: Mechanical Power (Watts)
        """
        # Relative speed of air hitting the runner
        # v_rel > 0 means air is pushing back against runner (drag)
        v_rel = velocity - wind_velocity_parallel
        
        # Drag force always opposes the relative air movement direction relative to runner?
        # Actually standard drag eq: Fd = 0.5 * rho * Cd * A * v_rel^2
        # Direction of force is opposite to relative velocity vector.
        # But we simply want magnitude of drag force *opposing motion*.
        
        # If v_rel > 0 (running into wind or faster than tailwind), Force is drag (positive cost).
        # If v_rel < 0 (strong tailwind faster than runner), Force is push (negative cost / assistance).
        
        force_drag = 0.5 * RunningPhysics.RHO_AIR * RunningPhysics.DRAG_COEFF * frontal_area * (v_rel**2) * np.sign(v_rel)
        
        # Mechanical power needed to maintain ground velocity against this force
        power_mech = force_drag * velocity
        return power_mech

    @staticmethod
    def mechanical_to_metabolic_power(mech_power, efficiency=0.25):
        """
        Convert mechanical power (like air resistance) to metabolic power (what the body burns).
        Standard gross efficiency for running is often cited around 20-25%.
        """
        return mech_power / efficiency

    @classmethod
    def calculate_total_power(cls, velocity, gradient, wind_speed, mass=65.0, frontal_area=0.4):
        """
        Calculate total METABOLIC power (Watts) required to run at a given speed 
        under given conditions.
        
        velocity: m/s
        gradient: decimal (fraction)
        wind_speed: m/s (Positive=Tailwind)
        mass: kg
        """
        if velocity <= 0:
            return 0.0

        # 1. Base Cost (Grade + Friction) from Minetti
        # Unit: J/kg/m * m/s * kg = J/s = Watts
        cost_per_meter = cls.minetti_cost_j_kg_m(gradient)
        p_base = cost_per_meter * mass * velocity
        
        # 2. Air Resistance Cost
        # Minetti's 3.6 constant theoretically includes minimal treadmill air resistance? 
        # Actually treadmill has zero air resistance. Outdoor running has 'still air' resistance.
        # So we should add air resistance for (v_run - v_wind).
        # If v_wind=0, we still have drag from v_run.
        
        # Scaling Frontal Area with Mass
        # Fixed area (0.4) gives unfair advantage to heavier runners (higher power/drag ratio).
        # We scale area based on mass (Square-cube law approx: Mass^(2/3)).
        # Baseline: 65kg -> 0.4 m^2? Actually 0.4 is a bit high for Cd*A. 
        # Cd ~0.9, A ~0.5? CdA ~ 0.45. Let's assume input frontal_area is CdA or Area? 
        # Docstring says "frontal_area: m^2". Code uses DRAG_COEFF * frontal_area. 
        # So "frontal_area" is A.
        # Let's scale A relative to 65kg standard.
        effective_area = frontal_area * ((mass / 65.0) ** (2.0/3.0))
        
        p_mech_drag = cls.calculate_drag_power_watts(velocity, wind_speed, effective_area)
        p_metabolic_drag = cls.mechanical_to_metabolic_power(p_mech_drag)
        
        return p_base + p_metabolic_drag

    @classmethod
    def solve_speed_for_power(cls, target_power, gradient, wind_speed, mass=65.0, frontal_area=0.4):
        """
        Find the running speed (m/s) that results in the given target metabolic power (Watts).
        Uses root finding since power is monotonic with speed in normal range.
        """
        
        def func(v):
            # calculate_total_power now handles mass-based area scaling
            return cls.calculate_total_power(v, gradient, wind_speed, mass, frontal_area) - target_power
            
        # Search range: 0.1 m/s (~27 min/km) to 10 m/s (world record sprint territory)
        try:
            # Check if even max speed is not enough (unlikely) or min speed is too much
            if func(0.1) > 0:
                return 0.1 # Too steep/hard to move
            
            speed = brentq(func, 0.1, 10.0)
            return speed
        except ValueError:
            # Should handle edge cases
            return 0.0

    @staticmethod
    def vdot_to_flat_velocity(vdot):
        """
        Approximate flat velocity (m/s) from VDOT.
        Using Daniels' formulas or approximation.
        Common approx formula for VDOT -> 
        VO2 = 3.5 + 0.2*speed(m/min) + 0.9*speed*grade?
        
        Daniels (2009) simplified:
        VO2 = -4.60 + 0.182258 * v + 0.000104 * v^2 
        where v is m/min.
        VDOT is essentially VO2max per min.
        """
        # We need to inverse the Daniels equation to find v from VO2.
        # VO2 = VDOT
        # 0.000104*v^2 + 0.182258*v - (VDOT + 4.60) = 0
        # Quadratic formula: ax^2 + bx + c = 0
        a = 0.000104
        b = 0.182258
        c = -(vdot + 4.60)
        
        # v = (-b + sqrt(b^2 - 4ac)) / 2a
        v_m_min = (-b + np.sqrt(b**2 - 4*a*c)) / (2*a)
        v_m_s = v_m_min / 60.0
        return v_m_s
