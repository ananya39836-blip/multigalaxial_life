"""
level_2/sensors.py - Simulated Multi-Modal Sensors & Perception Models
Part IV: Simulated Sensors and Perception
"""

import math
import numpy as np
from typing import List, Dict, Any, Tuple
from level_2.environment import PlanetaryTerrain, ResourceField


class ProximityRaycastSensor:
    """
    Multi-ray radial proximity rangefinder.
    Casts rays at specified azimuth angles, calculating distance to terrain or obstacles.
    """
    def __init__(
        self,
        sensor_id: str = "lidar_front",
        num_rays: int = 7,
        max_range: float = 12.0,
        fov_degrees: float = 120.0,
        noise_std: float = 0.05,
        dropout_prob: float = 0.01
    ):
        self.id = sensor_id
        self.num_rays = int(num_rays)
        self.max_range = float(max_range)
        self.fov = math.radians(fov_degrees)
        self.noise_std = float(noise_std)
        self.dropout_prob = float(dropout_prob)
        
        # Symmetrical ray angles relative to heading
        self.ray_angles = np.linspace(-self.fov / 2.0, self.fov / 2.0, self.num_rays)

    def read(
        self,
        pos: np.ndarray,
        heading: float,
        terrain: PlanetaryTerrain,
        obstacles: Optional[List[np.ndarray]] = None,
        rng: Optional[np.random.RandomState] = None
    ) -> Dict[str, Any]:
        """
        Executes raycasts from organism position.
        Returns ray distances, minimum obstacle distance, and detection vectors.
        """
        if rng is None:
            rng = np.random.RandomState()
            
        distances = []
        endpoints = []
        
        for angle in self.ray_angles:
            # Check for sensor dropout
            if rng.uniform(0, 1) < self.dropout_prob:
                distances.append(self.max_range)
                endpoints.append(pos[:2])
                continue
                
            abs_angle = heading + angle
            ray_dir = np.array([math.cos(abs_angle), math.sin(abs_angle)], dtype=np.float64)
            
            # Step along ray
            ray_dist = self.max_range
            step_size = 0.35
            cur_dist = step_size
            
            while cur_dist <= self.max_range:
                test_x = pos[0] + ray_dir[0] * cur_dist
                test_y = pos[1] + ray_dir[1] * cur_dist
                
                # Check terrain collision (slope step exceeding 0.45m)
                t_z = terrain.get_elevation(test_x, test_y)
                if t_z > pos[2] + 0.45:
                    ray_dist = cur_dist
                    break
                    
                # Check other obstacle positions
                hit_obstacle = False
                if obstacles:
                    for obs_pos in obstacles:
                        if math.hypot(test_x - obs_pos[0], test_y - obs_pos[1]) < 0.8:
                            ray_dist = cur_dist
                            hit_obstacle = True
                            break
                if hit_obstacle:
                    break
                    
                cur_dist += step_size
                
            # Add Gaussian measurement noise
            noisy_dist = max(0.0, min(self.max_range, ray_dist + rng.normal(0, self.noise_std)))
            distances.append(float(noisy_dist))
            
            hit_x = pos[0] + ray_dir[0] * noisy_dist
            hit_y = pos[1] + ray_dir[1] * noisy_dist
            endpoints.append((hit_x, hit_y))
            
        return {
            "sensor_id": self.id,
            "distances": distances,
            "min_distance": float(min(distances)),
            "ray_angles": self.ray_angles.tolist(),
            "endpoints": endpoints
        }


class ChemicalGradientSensor:
    """
    Simulates chemical chemoreceptors sampling local scalar nutrient field
    and computing local spatial gradient vectors (chemotaxis).
    """
    def __init__(
        self,
        sensor_id: str = "olfactory_sniffer",
        baseline_noise_std: float = 0.08,
        detection_threshold: float = 0.5,
        probe_radius: float = 1.0
    ):
        self.id = sensor_id
        self.noise_std = float(baseline_noise_std)
        self.threshold = float(detection_threshold)
        self.probe_radius = float(probe_radius)

    def read(
        self,
        pos: np.ndarray,
        heading: float,
        resource_field: ResourceField,
        rng: Optional[np.random.RandomState] = None
    ) -> Dict[str, Any]:
        """
        Samples nutrient concentration at organism center, left wing, and right wing.
        Computes forward-lateral chemical gradient.
        """
        if rng is None:
            rng = np.random.RandomState()
            
        c_center = resource_field.sample_concentration(pos[0], pos[1])
        
        # Left and right probe locations perpendicular to heading
        left_angle = heading + math.pi / 3.0
        right_angle = heading - math.pi / 3.0
        
        x_left = pos[0] + self.probe_radius * math.cos(left_angle)
        y_left = pos[1] + self.probe_radius * math.sin(left_angle)
        
        x_right = pos[0] + self.probe_radius * math.cos(right_angle)
        y_right = pos[1] + self.probe_radius * math.sin(right_angle)
        
        c_left = resource_field.sample_concentration(x_left, y_left)
        c_right = resource_field.sample_concentration(x_right, y_right)
        
        # Inject Gaussian sensor noise
        meas_center = max(0.0, c_center + rng.normal(0, self.noise_std))
        meas_left = max(0.0, c_left + rng.normal(0, self.noise_std))
        meas_right = max(0.0, c_right + rng.normal(0, self.noise_std))
        
        # Lateral steering bias for chemotaxis: positive = turn left, negative = turn right
        lateral_gradient = meas_left - meas_right
        
        detected = meas_center >= self.threshold or meas_left >= self.threshold or meas_right >= self.threshold
        
        return {
            "sensor_id": self.id,
            "detected": detected,
            "concentration_center": float(meas_center),
            "concentration_left": float(meas_left),
            "concentration_right": float(meas_right),
            "lateral_gradient": float(lateral_gradient)
        }


class VirtualCameraSensor:
    """
    Synthetic pinhole camera rendering low-resolution depth buffer and segmentation map.
    """
    def __init__(
        self,
        sensor_id: str = "rgb_depth_cam",
        resolution: Tuple[int, int] = (32, 32),
        fov_degrees: float = 75.0,
        max_depth: float = 25.0
    ):
        self.id = sensor_id
        self.width, self.height = resolution
        self.fov = math.radians(fov_degrees)
        self.max_depth = float(max_depth)

    def capture_frame(
        self,
        pos: np.ndarray,
        heading: float,
        terrain: PlanetaryTerrain,
        resource_field: ResourceField
    ) -> Dict[str, Any]:
        """
        Renders synthetic 2D raster buffers:
        - depth_map: normalized distance array [0, 1]
        - semantic_mask: [0: Sky, 1: Terrain, 2: Nutrient Rich Bloom]
        """
        depth_map = np.ones((self.height, self.width), dtype=np.float32)
        semantic_mask = np.zeros((self.height, self.width), dtype=np.uint8)
        
        angles_h = np.linspace(-self.fov / 2.0, self.fov / 2.0, self.width)
        
        for col_idx, angle in enumerate(angles_h):
            ray_heading = heading + angle
            dx = math.cos(ray_heading)
            dy = math.sin(ray_heading)
            
            for dist in np.linspace(1.0, self.max_depth, 20):
                tx = pos[0] + dx * dist
                ty = pos[1] + dy * dist
                tz = terrain.get_elevation(tx, ty)
                
                # Check line of sight intersection with ground plane
                view_z = pos[2] + 0.3 - dist * 0.1
                if tz >= view_z:
                    norm_depth = dist / self.max_depth
                    depth_map[:, col_idx] = norm_depth
                    
                    conc = resource_field.sample_concentration(tx, ty)
                    pixel_class = 2 if conc > 10.0 else 1
                    semantic_mask[:, col_idx] = pixel_class
                    break
                    
        return {
            "sensor_id": self.id,
            "depth_map": depth_map,
            "semantic_mask": semantic_mask,
            "resolution": (self.width, self.height)
        }


class IMUSensor:
    """
    Inertial Measurement Unit measuring 3-axis linear acceleration and yaw rate.
    """
    def __init__(self, sensor_id: str = "imu_core", accel_noise_std: float = 0.04, gyro_noise_std: float = 0.02):
        self.id = sensor_id
        self.accel_noise = accel_noise_std
        self.gyro_noise = gyro_noise_std
        self.prev_vel = np.zeros(3)

    def read(self, vel: np.ndarray, heading_rate: float, dt: float, rng: Optional[np.random.RandomState] = None) -> Dict[str, Any]:
        if rng is None:
            rng = np.random.RandomState()
            
        accel = (vel - self.prev_vel) / max(1e-4, dt)
        self.prev_vel = vel.copy()
        
        noisy_accel = accel + rng.normal(0, self.accel_noise, size=3)
        noisy_gyro = heading_rate + rng.normal(0, self.gyro_noise)
        
        return {
            "sensor_id": self.id,
            "acceleration": noisy_accel.tolist(),
            "yaw_rate": float(noisy_gyro)
        }
