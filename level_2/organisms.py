"""
level_2/organisms.py - Procedural Organism Morphology, Physiology & Lifecycle
Part III: Hypothetical Organism Modelling
"""

import math
import numpy as np
from typing import List, Dict, Any, Optional


class MetabolicBudget:
    """
    Thermodynamic metabolic energy accounting.
    Enforces the First Law of Thermodynamics:
    dE/dt = E_intake - E_basal - E_kinetic - E_compute - E_sensor.
    """
    def __init__(
        self,
        mass_kg: float = 12.0,
        initial_energy_j: float = 1000.0,
        max_energy_j: float = 2500.0,
        metabolic_efficiency: float = 0.85
    ):
        self.mass = float(mass_kg)
        self.energy = float(initial_energy_j)
        self.max_energy = float(max_energy_j)
        self.efficiency = float(metabolic_efficiency)
        self.health = 1.0  # Normalized [0.0, 1.0]
        
        # Kleiber's Law: E_basal proportional to M^0.75
        self.basal_rate_w = 0.5 * (self.mass ** 0.75)
        self.cumulative_ingested = 0.0
        self.cumulative_spent = 0.0

    def step_metabolism(
        self,
        speed: float,
        sensor_power_w: float = 0.2,
        compute_power_w: float = 0.4,
        dt: float = 0.02
    ) -> bool:
        """
        Deducts metabolic costs for time interval dt.
        Returns True if organism is alive, False if energy exhausted (starvation).
        """
        # Locomotion cost: quadratic with speed
        locomotion_power_w = 0.8 * self.mass * (speed ** 2)
        total_power = self.basal_rate_w + locomotion_power_w + sensor_power_w + compute_power_w
        energy_spent = (total_power / self.efficiency) * dt
        
        self.energy -= energy_spent
        self.cumulative_spent += energy_spent
        
        if self.energy <= 0.0:
            self.energy = 0.0
            self.health -= 0.1 * dt  # Starvation damage
            if self.health <= 0.0:
                self.health = 0.0
                return False  # Dead
        else:
            # Slow health regeneration if well-fed (> 50% energy)
            if self.energy > 0.5 * self.max_energy and self.health < 1.0:
                self.health = min(1.0, self.health + 0.02 * dt)
                
        return self.health > 0.0

    def ingest_energy(self, amount_j: float):
        """Adds digested energy from harvested environmental resources."""
        usable = float(amount_j) * self.efficiency
        self.energy = min(self.max_energy, self.energy + usable)
        self.cumulative_ingested += usable


class OrganismMorphology:
    """
    Kinematic structural model: articulated body segments, appendages,
    and joint limits for procedural animation.
    """
    def __init__(
        self,
        archetype: str = "Hexapod_Forager",
        num_segments: int = 3,
        num_appendages: int = 6,
        body_length: float = 1.2,
        body_width: float = 0.6,
        body_height: float = 0.35,
        color_rgb: Tuple[float, float, float] = (0.2, 0.7, 0.9)
    ):
        self.archetype = archetype
        self.num_segments = int(num_segments)
        self.num_appendages = int(num_appendages)
        self.length = float(body_length)
        self.width = float(body_width)
        self.height = float(body_height)
        self.color = color_rgb
        
        # Relative segment lengths
        self.segment_offsets = np.linspace(-self.length / 2.0, self.length / 2.0, self.num_segments)
        
        # Limb attachment sockets [(seg_idx, side: -1 or 1, leg_len)]
        self.limbs = []
        for i in range(self.num_appendages):
            side = -1 if i % 2 == 0 else 1
            seg = i // 2
            self.limbs.append({
                "limb_id": i,
                "segment_index": min(seg, self.num_segments - 1),
                "side": side,
                "femur_len": 0.35,
                "tibia_len": 0.40,
                "phase_offset": (i * np.pi / 3.0) % (2.0 * np.pi)
            })


class Organism:
    """
    Autonomous artificial-life organism integrating morphology,
    physiology, state kinematics, sensors, and controller interfaces.
    """
    def __init__(
        self,
        organism_id: str,
        initial_pos: np.ndarray,
        initial_heading: float = 0.0,
        morphology: Optional[OrganismMorphology] = None,
        mass_kg: float = 12.0,
        initial_energy_j: float = 1000.0
    ):
        self.id = str(organism_id)
        self.pos = np.array(initial_pos, dtype=np.float64)
        self.vel = np.zeros(3, dtype=np.float64)
        self.heading = float(initial_heading)
        
        self.morphology = morphology or OrganismMorphology()
        self.physiology = MetabolicBudget(mass_kg=mass_kg, initial_energy_j=initial_energy_j)
        
        self.age = 0.0
        self.is_alive = True
        self.fsm_state = "FORAGE"
        self.current_action = {"throttle": 0.0, "steering": 0.0}
        
        # Sensor data cache
        self.sensor_readings: Dict[str, Any] = {}
        # Trajectory telemetry history
        self.trajectory_history: List[Tuple[float, float, float]] = []

    def update_pose(self, new_pos: np.ndarray, new_vel: np.ndarray, new_heading: float, dt: float):
        """Update kinematic state and append to trajectory history."""
        self.pos = new_pos
        self.vel = new_vel
        self.heading = new_heading
        self.age += dt
        
        # Record trajectory sample periodically or on displacement
        self.traj_step = getattr(self, 'traj_step', 0) + 1
        if len(self.trajectory_history) == 0 or self.traj_step % 10 == 0 or np.linalg.norm(self.pos - self.trajectory_history[-1]) > 0.1:
            self.trajectory_history.append((float(self.pos[0]), float(self.pos[1]), float(self.pos[2])))
            if len(self.trajectory_history) > 500:
                self.trajectory_history.pop(0)

    def can_reproduce(self, threshold_j: float = 2000.0) -> bool:
        """Returns True if energy exceeds reproduction threshold."""
        return self.is_alive and self.physiology.energy >= threshold_j

    def spawn_offspring(self, new_id: str, mutation_rate: float = 0.05) -> 'Organism':
        """Spawns mutated offspring organism, dividing parent energy in half."""
        half_energy = self.physiology.energy * 0.45
        self.physiology.energy *= 0.50
        
        # Slight positional offset
        offset = np.array([np.random.uniform(-1.0, 1.0), np.random.uniform(-1.0, 1.0), 0.0])
        child_pos = self.pos + offset
        
        # Mutate mass slightly
        mutated_mass = max(2.0, self.physiology.mass * (1.0 + np.random.uniform(-mutation_rate, mutation_rate)))
        
        child = Organism(
            organism_id=new_id,
            initial_pos=child_pos,
            initial_heading=self.heading + np.random.uniform(-0.5, 0.5),
            morphology=self.morphology,
            mass_kg=mutated_mass,
            initial_energy_j=half_energy
        )
        return child


class OrganismTemplateLibrary:
    """Pre-configured standard biological archetypes."""
    @staticmethod
    def create_hexapod_forager(org_id: str, x: float, y: float, z: float) -> Organism:
        morph = OrganismMorphology(
            archetype="Hexapod_Forager",
            num_segments=3,
            num_appendages=6,
            body_length=1.4,
            body_width=0.7,
            body_height=0.35,
            color_rgb=(0.2, 0.75, 0.95)
        )
        return Organism(org_id, np.array([x, y, z]), morphology=morph, mass_kg=14.0, initial_energy_j=1200.0)

    @staticmethod
    def create_aquatic_serpentine(org_id: str, x: float, y: float, z: float) -> Organism:
        morph = OrganismMorphology(
            archetype="Aquatic_Serpentine",
            num_segments=6,
            num_appendages=2,
            body_length=2.2,
            body_width=0.4,
            body_height=0.3,
            color_rgb=(0.2, 0.9, 0.4)
        )
        return Organism(org_id, np.array([x, y, z]), morphology=morph, mass_kg=8.5, initial_energy_j=900.0)

    @staticmethod
    def create_apex_predator(org_id: str, x: float, y: float, z: float) -> Organism:
        morph = OrganismMorphology(
            archetype="Apex_Predator",
            num_segments=4,
            num_appendages=4,
            body_length=1.8,
            body_width=0.8,
            body_height=0.5,
            color_rgb=(0.95, 0.25, 0.25)
        )
        return Organism(org_id, np.array([x, y, z]), morphology=morph, mass_kg=28.0, initial_energy_j=2200.0)
