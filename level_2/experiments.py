"""
level_2/experiments.py - Simulation Orchestration, Experiment Runner & Telemetry Logging
Part VIII: Experimentation, Validation, and Deployment
"""

import os
import json
import time
import math
import hashlib
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional

from level_2.environment import PlanetaryTerrain, AtmosphericField, ResourceField, PhysicsSimulator
from level_2.organisms import Organism, OrganismTemplateLibrary
from level_2.sensors import ProximityRaycastSensor, ChemicalGradientSensor, VirtualCameraSensor
from level_2.processors import VirtualMicroprocessor
from level_2.controllers import FSMController


class SimulationOrchestrator:
    """
    Main real-time simulation coordinator integrating environment, organisms,
    sensors, virtual microprocessors, controllers, and physics.
    """
    def __init__(
        self,
        terrain_roughness: float = 1.0,
        gravity: float = 9.81,
        seed: int = 42
    ):
        self.seed = int(seed)
        self.rng = np.random.RandomState(self.seed)
        
        # Subsystem instantiation
        self.terrain = PlanetaryTerrain(size_x=100.0, size_y=100.0, grid_res=64, seed=self.seed, roughness=terrain_roughness)
        self.atmosphere = AtmosphericField(surface_gravity=gravity)
        self.resource_field = ResourceField(size_x=100.0, size_y=100.0, grid_res=50, seed=self.seed)
        self.physics = PhysicsSimulator(self.terrain, self.atmosphere)
        
        # Agents & Subsystems
        self.organisms: List[Organism] = []
        self.processors: Dict[str, VirtualMicroprocessor] = {}
        self.controllers: Dict[str, FSMController] = {}
        self.lidars: Dict[str, ProximityRaycastSensor] = {}
        self.chem_sensors: Dict[str, ChemicalGradientSensor] = {}
        self.cameras: Dict[str, VirtualCameraSensor] = {}
        
        self.simulation_time = 0.0
        self.step_count = 0
        self.telemetry_records: List[Dict[str, Any]] = []

    def spawn_organism(
        self,
        archetype: str = "Hexapod_Forager",
        x: float = 0.0,
        y: float = 0.0,
        clock_hz: float = 500.0
    ) -> Organism:
        """Instantiates organism, virtual CPU, sensors, and controller."""
        org_id = f"ORG_{len(self.organisms)+1:03d}"
        z = self.terrain.get_elevation(x, y) + 0.35
        
        if archetype == "Aquatic_Serpentine":
            org = OrganismTemplateLibrary.create_aquatic_serpentine(org_id, x, y, z)
        elif archetype == "Apex_Predator":
            org = OrganismTemplateLibrary.create_apex_predator(org_id, x, y, z)
        else:
            org = OrganismTemplateLibrary.create_hexapod_forager(org_id, x, y, z)
            
        self.organisms.append(org)
        self.processors[org_id] = VirtualMicroprocessor(processor_id=f"vCPU_{org_id}", clock_frequency_hz=clock_hz)
        self.controllers[org_id] = FSMController()
        self.lidars[org_id] = ProximityRaycastSensor(sensor_id=f"lidar_{org_id}")
        self.chem_sensors[org_id] = ChemicalGradientSensor(sensor_id=f"chem_{org_id}")
        self.cameras[org_id] = VirtualCameraSensor(sensor_id=f"cam_{org_id}")
        
        return org

    def step(self, dt: float = 0.02):
        """
        Executes one complete simulation cycle across all subsystems.
        """
        self.simulation_time += dt
        self.step_count += 1
        
        # 1. Update environmental resource field diffusion
        self.resource_field.step(dt)
        
        for org in self.organisms:
            if not org.is_alive:
                continue
                
            org_id = org.id
            vcpu = self.processors[org_id]
            fsm = self.controllers[org_id]
            lidar = self.lidars[org_id]
            chem = self.chem_sensors[org_id]
            
            # Exclude self from obstacle detection
            other_positions = [o.pos[:2] for o in self.organisms if o.is_alive and o.id != org_id]
            
            # A. SENSOR READINGS
            lidar_data = lidar.read(org.pos, org.heading, self.terrain, obstacles=other_positions, rng=self.rng)
            chem_data = chem.read(org.pos, org.heading, self.resource_field, rng=self.rng)
            org.sensor_readings["lidar_front"] = lidar_data
            org.sensor_readings["chem"] = chem_data
            
            # B. CONTROLLER DECISION
            action, instructions = fsm.step(
                current_heading=org.heading,
                energy_j=org.physiology.energy,
                lidar_data=lidar_data,
                chemical_data=chem_data,
                dt=dt
            )
            org.fsm_state = fsm.current_state
            org.current_action = action
            
            # C. VIRTUAL CPU EXECUTION (Throttling & Latency Accounting)
            cpu_stats = vcpu.execute_routine(instructions, simulation_step_dt=dt)
            
            # D. METABOLISM & RESOURCE HARVESTING
            speed = float(np.linalg.norm(org.vel[:2]))
            alive = org.physiology.step_metabolism(
                speed=speed,
                sensor_power_w=0.15,
                compute_power_w=cpu_stats["energy_consumed_j"] / dt,
                dt=dt
            )
            org.is_alive = alive
            
            # Harvest resource if near nutrient bloom
            if org.fsm_state in ["FORAGE", "WANDER"]:
                harvested = self.resource_field.consume_resource(org.pos[0], org.pos[1], amount=3.5 * dt)
                if harvested > 0.0:
                    org.physiology.ingest_energy(harvested * 50.0)
                    
            # E. KINEMATIC INTEGRATION
            new_pos, new_vel, new_heading = self.physics.step_organism_kinematics(
                pos=org.pos,
                vel=org.vel,
                heading=org.heading,
                throttle=action["throttle"],
                steering=action["steering"],
                mass=org.physiology.mass,
                dt=dt
            )
            org.update_pose(new_pos, new_vel, new_heading, dt)
            
            # F. TELEMETRY LOG RECORD
            if self.step_count % 5 == 0:
                self.telemetry_records.append({
                    "step": self.step_count,
                    "time_sec": round(self.simulation_time, 3),
                    "organism_id": org_id,
                    "x": round(float(org.pos[0]), 3),
                    "y": round(float(org.pos[1]), 3),
                    "z": round(float(org.pos[2]), 3),
                    "speed": round(speed, 3),
                    "heading_deg": round(math.degrees(org.heading), 1),
                    "fsm_state": org.fsm_state,
                    "energy_j": round(org.physiology.energy, 2),
                    "health": round(org.physiology.health, 3),
                    "min_lidar_dist": round(lidar_data["min_distance"], 2),
                    "chem_concentration": round(chem_data["concentration_center"], 2),
                    "cpu_cycles": cpu_stats["cycles_executed"],
                    "missed_deadlines": cpu_stats["missed_deadlines_total"]
                })


class ExperimentRunner:
    """
    Automated scientific trial execution across independent parameter variations.
    Saves reproducible logs with cryptographic SHA-256 provenance hashes.
    """
    @staticmethod
    def run_foraging_experiment(
        num_trials: int = 5,
        clock_hz_values: Optional[List[float]] = None,
        max_steps: int = 500,
        out_dir: str = r"C:\Users\HP\.gemini\antigravity\scratch\multigalaxial_life\level_2\results"
    ) -> Dict[str, Any]:
        """
        Executes Landmark Experiment 01: Foraging efficiency vs. Virtual CPU compute budget.
        """
        os.makedirs(out_dir, exist_ok=True)
        if clock_hz_values is None:
            clock_hz_values = [50.0, 200.0, 1000.0]
            
        results = []
        
        for clk in clock_hz_values:
            for trial in range(num_trials):
                seed = 1000 + trial * 17
                sim = SimulationOrchestrator(seed=seed)
                # Spawn single organism
                org = sim.spawn_organism(archetype="Hexapod_Forager", x=0.0, y=0.0, clock_hz=clk)
                
                start_energy = org.physiology.energy
                for _ in range(max_steps):
                    if not org.is_alive:
                        break
                    sim.step(dt=0.02)
                    
                net_energy = org.physiology.cumulative_ingested - org.physiology.cumulative_spent
                distance_traveled = float(np.sum([
                    np.linalg.norm(np.array(sim.organisms[0].trajectory_history[i]) - np.array(sim.organisms[0].trajectory_history[i-1]))
                    for i in range(1, len(sim.organisms[0].trajectory_history))
                ])) if len(sim.organisms[0].trajectory_history) > 1 else 0.0
                
                results.append({
                    "clock_hz": clk,
                    "trial": trial + 1,
                    "seed": seed,
                    "survived": org.is_alive,
                    "final_time_sec": round(sim.simulation_time, 2),
                    "final_energy_j": round(org.physiology.energy, 2),
                    "net_energy_j": round(net_energy, 2),
                    "distance_m": round(distance_traveled, 2),
                    "missed_deadlines": sim.processors[org.id].missed_deadlines
                })
                
        df = pd.DataFrame(results)
        csv_path = os.path.join(out_dir, "experiment_01_foraging_benchmark.csv")
        df.to_csv(csv_path, index=False)
        
        with open(csv_path, "rb") as f:
            sha256 = hashlib.sha256(f.read()).hexdigest()
            
        summary = {
            "experiment_id": "EXP-L2-01-FORAGING",
            "trials_executed": len(results),
            "csv_path": csv_path,
            "sha256_provenance": sha256,
            "mean_energy_by_clock": df.groupby("clock_hz")["net_energy_j"].mean().to_dict(),
            "mean_deadlines_by_clock": df.groupby("clock_hz")["missed_deadlines"].mean().to_dict()
        }
        
        json_path = os.path.join(out_dir, "experiment_01_summary.json")
        with open(json_path, "w") as f:
            json.dump(summary, f, indent=4)
            
        return summary
