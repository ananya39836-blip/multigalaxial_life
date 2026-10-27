"""
level_2/environment.py - Planetary Terrain, Atmosphere, Resource Fields & Physics
Part II: Procedural 3D Planetary Worlds & Environmental Physics
"""

import math
import numpy as np
from typing import Tuple, Dict, Any, Optional


class PlanetaryTerrain:
    """
    Procedural 2.5D planetary terrain generator with multi-octave harmonic elevation,
    slope calculation, and continuous surface normal estimation.
    """
    def __init__(
        self,
        size_x: float = 100.0,
        size_y: float = 100.0,
        grid_res: int = 64,
        seed: int = 42,
        roughness: float = 1.0,
        crater_density: float = 0.05
    ):
        self.size_x = float(size_x)
        self.size_y = float(size_y)
        self.grid_res = int(grid_res)
        self.seed = int(seed)
        self.roughness = float(roughness)
        self.crater_density = float(crater_density)
        
        self.dx = self.size_x / (self.grid_res - 1)
        self.dy = self.size_y / (self.grid_res - 1)
        
        self.heightfield = self._generate_heightfield()

    def _generate_heightfield(self) -> np.ndarray:
        rng = np.random.RandomState(self.seed)
        x = np.linspace(-self.size_x / 2.0, self.size_x / 2.0, self.grid_res)
        y = np.linspace(-self.size_y / 2.0, self.size_y / 2.0, self.grid_res)
        xx, yy = np.meshgrid(x, y)
        
        # Multi-octave continuous harmonic elevation
        z = np.zeros_like(xx)
        octaves = [
            (0.02, 8.0 * self.roughness),
            (0.05, 3.5 * self.roughness),
            (0.12, 1.2 * self.roughness),
            (0.25, 0.4 * self.roughness)
        ]
        
        for freq, amp in octaves:
            phase_x = rng.uniform(0, 2 * np.pi)
            phase_y = rng.uniform(0, 2 * np.pi)
            z += amp * np.sin(freq * xx + phase_x) * np.cos(freq * yy + phase_y)
            
        # Add impact craters
        n_craters = int(self.crater_density * (self.size_x * self.size_y / 100.0))
        for _ in range(n_craters):
            cx = rng.uniform(-self.size_x / 2.5, self.size_x / 2.5)
            cy = rng.uniform(-self.size_y / 2.5, self.size_y / 2.5)
            r = rng.uniform(4.0, 15.0)
            depth = rng.uniform(1.5, 4.0) * self.roughness
            
            dist_sq = (xx - cx)**2 + (yy - cy)**2
            # Parabolic depression with elevated rim
            crater_mask = dist_sq < (r * 1.3)**2
            depression = -depth * np.maximum(0.0, 1.0 - dist_sq / (r**2))
            rim = (depth * 0.35) * np.exp(-((np.sqrt(dist_sq) - r)**2) / 4.0)
            z += (depression + rim) * crater_mask
            
        return z

    def get_elevation(self, x: float, y: float) -> float:
        """Bilinear interpolation of terrain elevation z = h(x, y)."""
        gx = (x + self.size_x / 2.0) / self.dx
        gy = (y + self.size_y / 2.0) / self.dy
        
        gx = max(0.0, min(self.grid_res - 1.001, gx))
        gy = max(0.0, min(self.grid_res - 1.001, gy))
        
        x0, y0 = int(gx), int(gy)
        x1, y1 = min(self.grid_res - 1, x0 + 1), min(self.grid_res - 1, y0 + 1)
        
        fx = gx - x0
        fy = gy - y0
        
        h00 = self.heightfield[y0, x0]
        h10 = self.heightfield[y0, x1]
        h01 = self.heightfield[y1, x0]
        h11 = self.heightfield[y1, x1]
        
        return float((1 - fx) * (1 - fy) * h00 + fx * (1 - fy) * h10 + (1 - fx) * fy * h01 + fx * fy * h11)

    def get_surface_normal(self, x: float, y: float, eps: float = 0.5) -> np.ndarray:
        """Computes normalized surface normal vector n at (x, y)."""
        h_x1 = self.get_elevation(x + eps, y)
        h_x0 = self.get_elevation(x - eps, y)
        h_y1 = self.get_elevation(x, y + eps)
        h_y0 = self.get_elevation(x, y - eps)
        
        dz_dx = (h_x1 - h_x0) / (2.0 * eps)
        dz_dy = (h_y1 - h_y0) / (2.0 * eps)
        
        n = np.array([-dz_dx, -dz_dy, 1.0], dtype=np.float64)
        norm = np.linalg.norm(n)
        return n / norm if norm > 1e-6 else np.array([0.0, 0.0, 1.0])

    def get_slope_degrees(self, x: float, y: float) -> float:
        """Slope angle in degrees relative to horizontal ground."""
        n = self.get_surface_normal(x, y)
        cos_theta = np.clip(n[2], -1.0, 1.0)
        return float(np.degrees(np.arccos(cos_theta)))


class AtmosphericField:
    """
    Physical planetary atmospheric model: gravity, barometric pressure,
    atmospheric density, temperature lapse rate, and horizontal wind vectors.
    """
    def __init__(
        self,
        surface_gravity: float = 9.81,
        surface_pressure_bar: float = 1.013,
        surface_temp_k: float = 288.15,
        scale_height_m: float = 8500.0,
        wind_speed_ms: float = 2.5,
        wind_heading_deg: float = 45.0
    ):
        self.g = float(surface_gravity)
        self.p0 = float(surface_pressure_bar)
        self.t0 = float(surface_temp_k)
        self.scale_height = float(scale_height_m)
        self.wind_speed = float(wind_speed_ms)
        self.wind_heading = math.radians(wind_heading_deg)
        
        self.lapse_rate = 0.0065  # K/m temperature decrease

    def get_density(self, z: float) -> float:
        """Atmospheric mass density rho(z) in kg/m^3."""
        p = self.p0 * 1e5 * math.exp(-max(0.0, z) / self.scale_height)
        t = max(50.0, self.t0 - self.lapse_rate * max(0.0, z))
        r_specific = 287.058  # J/(kg K)
        return p / (r_specific * t)

    def get_temperature(self, z: float) -> float:
        """Ambient temperature in Kelvin."""
        return max(50.0, self.t0 - self.lapse_rate * max(0.0, z))

    def get_wind_vector(self) -> np.ndarray:
        """Horizontal wind velocity [vx, vy, 0]."""
        return np.array([
            self.wind_speed * math.cos(self.wind_heading),
            self.wind_speed * math.sin(self.wind_heading),
            0.0
        ], dtype=np.float64)


class ResourceField:
    """
    Continuous 2D spatial diffusion resource grid for nutrients and environmental hazards.
    Governed by reaction-diffusion: dS/dt = D grad^2 S + r S (1 - S/K) - consumption.
    """
    def __init__(
        self,
        size_x: float = 100.0,
        size_y: float = 100.0,
        grid_res: int = 50,
        diffusion_coeff: float = 0.05,
        growth_rate: float = 0.08,
        carrying_capacity: float = 100.0,
        seed: int = 42
    ):
        self.size_x = float(size_x)
        self.size_y = float(size_y)
        self.res = int(grid_res)
        self.D = float(diffusion_coeff)
        self.r = float(growth_rate)
        self.K = float(carrying_capacity)
        
        self.dx = self.size_x / self.res
        self.dy = self.size_y / self.res
        
        rng = np.random.RandomState(seed)
        # Initialize patchy resource blooms
        self.grid = np.zeros((self.res, self.res), dtype=np.float64)
        n_patches = 8
        for _ in range(n_patches):
            px = rng.randint(5, self.res - 5)
            py = rng.randint(5, self.res - 5)
            rad = rng.uniform(3.0, 7.0)
            peak = rng.uniform(60.0, 95.0)
            
            y, x = np.ogrid[:self.res, :self.res]
            dist_sq = (x - px)**2 + (y - py)**2
            self.grid += peak * np.exp(-dist_sq / (2.0 * rad**2))
            
        self.grid = np.clip(self.grid, 0.0, self.K)

    def sample_concentration(self, x: float, y: float) -> float:
        """Sample resource concentration at world position (x, y)."""
        gx = int(round((x + self.size_x / 2.0) / self.dx))
        gy = int(round((y + self.size_y / 2.0) / self.dy))
        
        if 0 <= gx < self.res and 0 <= gy < self.res:
            return float(self.grid[gy, gx])
        return 0.0

    def consume_resource(self, x: float, y: float, amount: float) -> float:
        """Consume resource from localized grid cell, returning harvested amount."""
        gx = int(round((x + self.size_x / 2.0) / self.dx))
        gy = int(round((y + self.size_y / 2.0) / self.dy))
        
        if 0 <= gx < self.res and 0 <= gy < self.res:
            avail = self.grid[gy, gx]
            harvested = min(avail, float(amount))
            self.grid[gy, gx] -= harvested
            return harvested
        return 0.0

    def step(self, dt: float = 0.1):
        """Update reaction-diffusion step."""
        # 5-point discrete Laplacian for spatial diffusion
        laplacian = (
            np.roll(self.grid, 1, axis=0) + np.roll(self.grid, -1, axis=0) +
            np.roll(self.grid, 1, axis=1) + np.roll(self.grid, -1, axis=1) -
            4.0 * self.grid
        ) / (self.dx * self.dy)
        
        # Logistic local regrowth
        growth = self.r * self.grid * (1.0 - self.grid / self.K)
        
        self.grid += dt * (self.D * laplacian + growth)
        self.grid = np.clip(self.grid, 0.0, self.K)


class PhysicsSimulator:
    """
    Semi-implicit Euler rigid-body kinematic integration with terrain collision,
    surface Coulomb friction, and aerodynamic fluid drag.
    """
    def __init__(self, terrain: PlanetaryTerrain, atmosphere: AtmosphericField):
        self.terrain = terrain
        self.atmosphere = atmosphere
        
    def step_organism_kinematics(
        self,
        pos: np.ndarray,
        vel: np.ndarray,
        heading: float,
        throttle: float,
        steering: float,
        mass: float,
        drag_coeff: float = 0.45,
        frontal_area: float = 0.35,
        friction_coeff: float = 0.40,
        dt: float = 0.02
    ) -> Tuple[np.ndarray, np.ndarray, float]:
        """
        Integrates kinematics for a single organism step.
        Returns: (new_pos, new_vel, new_heading)
        """
        # Update heading
        new_heading = (heading + steering * dt) % (2.0 * math.pi)
        
        # Forward propulsion force
        propulsion_dir = np.array([math.cos(new_heading), math.sin(new_heading), 0.0], dtype=np.float64)
        f_prop = throttle * propulsion_dir
        
        # Atmospheric aerodynamic drag
        density = self.atmosphere.get_density(pos[2])
        v_rel = vel - self.atmosphere.get_wind_vector()
        v_mag = np.linalg.norm(v_rel)
        f_drag = -0.5 * density * (v_mag**2) * drag_coeff * frontal_area * (v_rel / (v_mag + 1e-6))
        
        # Gravity
        f_grav = np.array([0.0, 0.0, -mass * self.atmosphere.g], dtype=np.float64)
        
        # Net force before ground contact
        f_net = f_prop + f_drag + f_grav
        
        # Euler velocity integration
        accel = f_net / max(0.1, mass)
        new_vel = vel + accel * dt
        new_pos = pos + new_vel * dt
        
        # Terrain collision resolution
        terrain_z = self.terrain.get_elevation(new_pos[0], new_pos[1])
        ground_clearance = 0.25  # Organism resting elevation
        
        if new_pos[2] <= terrain_z + ground_clearance:
            new_pos[2] = terrain_z + ground_clearance
            # Zero out vertical velocity on ground
            new_vel[2] = 0.0
            
            # Apply ground rolling / locomotion resistance to horizontal motion
            h_speed = math.sqrt(new_vel[0]**2 + new_vel[1]**2)
            if h_speed > 1e-4:
                c_roll = 0.05 * friction_coeff  # Locomotive rolling resistance coefficient
                normal_force = mass * self.atmosphere.g
                f_friction = c_roll * normal_force
                friction_decel = (f_friction / mass) * dt
                reduction = max(0.0, 1.0 - friction_decel / h_speed)
                new_vel[0] *= reduction
                new_vel[1] *= reduction
            else:
                new_vel[0] = 0.0
                new_vel[1] = 0.0

        # Boundary clamping to terrain dimensions
        half_x = self.terrain.size_x / 2.0 - 1.0
        half_y = self.terrain.size_y / 2.0 - 1.0
        new_pos[0] = np.clip(new_pos[0], -half_x, half_x)
        new_pos[1] = np.clip(new_pos[1], -half_y, half_y)
        
        return new_pos, new_vel, new_heading
