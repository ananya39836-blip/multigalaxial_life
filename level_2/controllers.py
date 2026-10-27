"""
level_2/controllers.py - Behavioral Controllers, FSMs, Behavior Trees & PID
Part V: Controllers, Microprocessors, and Embedded Systems
"""

import math
from typing import Dict, Any, Tuple


class HeadingPIDController:
    """
    Closed-loop Proportional-Integral-Derivative (PID) controller for steering angle regulation.
    u(t) = Kp * e(t) + Ki * integral(e) + Kd * de/dt.
    """
    def __init__(self, kp: float = 1.8, ki: float = 0.05, kd: float = 0.35, max_steering_rate: float = 2.5):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.max_rate = float(max_steering_rate)
        
        self.integral = 0.0
        self.prev_error = 0.0

    def compute_steering(self, target_heading: float, current_heading: float, dt: float = 0.02) -> float:
        """Computes bounded steering rate (rad/s) to track target heading."""
        # Smallest signed angle difference in [-pi, pi]
        error = (target_heading - current_heading + math.pi) % (2.0 * math.pi) - math.pi
        
        # Anti-windup clamped integration
        self.integral = max(-1.0, min(1.0, self.integral + error * dt))
        derivative = (error - self.prev_error) / max(1e-4, dt)
        self.prev_error = error
        
        u = self.kp * error + self.ki * self.integral + self.kd * derivative
        return max(-self.max_rate, min(self.max_rate, u))


class FSMController:
    """
    Deterministic Finite State Machine (FSM) behavioral controller.
    Supported states:
    - FORAGE: Gradient-climbing toward detected nutrients.
    - AVOID_OBSTACLE: Repulsion from steep slopes or obstacles detected via lidar.
    - REST_METABOLIZE: Reduced movement to conserve energy when starving.
    - REPRODUCE: High-energy state preparing asexual division.
    - WANDER: Exploratory search when no gradient is detected.
    """
    def __init__(self, obstacle_clearance_m: float = 1.8, starvation_energy_j: float = 200.0):
        self.current_state = "WANDER"
        self.obstacle_clearance = float(obstacle_clearance_m)
        self.starvation_energy = float(starvation_energy_j)
        self.pid = HeadingPIDController()
        
        self.wander_timer = 0.0
        self.wander_turn = 0.0

    def step(
        self,
        current_heading: float,
        energy_j: float,
        lidar_data: Dict[str, Any],
        chemical_data: Dict[str, Any],
        dt: float = 0.02
    ) -> Tuple[Dict[str, float], Dict[str, int]]:
        """
        Processes sensor inputs, evaluates state transitions, and outputs action commands.
        Returns: (action_dict, instruction_counts)
        """
        # Instruction profiling for Virtual CPU
        instructions = {
            "SENSOR_READ": 4,
            "ARITHMETIC": 8,
            "LOGIC_BRANCH": 6,
            "STATE_TRANSITION": 0,
            "MOTOR_COMMAND": 2
        }
        
        min_dist = lidar_data.get("min_distance", 10.0)
        chem_detected = chemical_data.get("detected", False)
        lat_grad = chemical_data.get("lateral_gradient", 0.0)
        
        prev_state = self.current_state
        
        # State Transition Guards
        if min_dist < self.obstacle_clearance:
            self.current_state = "AVOID_OBSTACLE"
        elif energy_j < self.starvation_energy:
            self.current_state = "REST_METABOLIZE"
        elif chem_detected:
            self.current_state = "FORAGE"
        else:
            self.current_state = "WANDER"
            
        if self.current_state != prev_state:
            instructions["STATE_TRANSITION"] = 1
            
        # Action Synthesis based on Active State
        throttle = 0.0
        steering = 0.0
        
        if self.current_state == "AVOID_OBSTACLE":
            # Turn sharply away from obstacle
            throttle = 2.0  # Slow down
            steering = 2.0  # Sharp turn
        elif self.current_state == "REST_METABOLIZE":
            # Conserve energy, creep forward slowly
            throttle = 1.0
            steering = 0.0
        elif self.current_state == "FORAGE":
            # Chemotaxis: steer towards higher chemical concentration
            throttle = 8.5
            target_heading = current_heading + (1.2 if lat_grad > 0.0 else -1.2)
            steering = self.pid.compute_steering(target_heading, current_heading, dt=dt)
        else:  # WANDER
            self.wander_timer -= dt
            if self.wander_timer <= 0.0:
                self.wander_timer = 2.5
                self.wander_turn = float(np.random.uniform(-1.0, 1.0)) if 'np' in globals() else 0.5
            throttle = 5.0
            steering = self.wander_turn
            
        action = {"throttle": float(throttle), "steering": float(steering)}
        return action, instructions
