"""
level_2/tests_level_2.py - Comprehensive Verification of the 14 Acceptance Tests
Section 13: Acceptance Tests Specification
"""

import os
import math
import numpy as np
import pytest

from level_2.environment import PlanetaryTerrain, AtmosphericField, ResourceField, PhysicsSimulator
from level_2.organisms import Organism, OrganismMorphology, OrganismTemplateLibrary
from level_2.sensors import ProximityRaycastSensor, ChemicalGradientSensor, VirtualCameraSensor, IMUSensor
from level_2.processors import VirtualMicroprocessor
from level_2.controllers import FSMController, HeadingPIDController
from level_2.animation import ProceduralIK, GaitGenerator, Visual3DStudio
from level_2.experiments import SimulationOrchestrator, ExperimentRunner


class TestLevel2AcceptanceSuite:
    """Rigorous verification suite for Level 2 Acceptance Criteria."""

    def test_01_application_startup(self):
        """TEST 1: Application startup verification."""
        sim = SimulationOrchestrator(seed=42)
        assert sim is not None
        assert sim.step_count == 0
        assert sim.simulation_time == 0.0

    def test_02_environment_generation(self):
        """TEST 2: Environment generation (terrain, atmosphere, resources)."""
        terrain = PlanetaryTerrain(size_x=50.0, size_y=50.0, grid_res=32, roughness=1.2)
        assert terrain.heightfield.shape == (32, 32)
        
        # Test elevation continuity
        z1 = terrain.get_elevation(0.0, 0.0)
        z2 = terrain.get_elevation(0.1, 0.1)
        assert abs(z1 - z2) < 1.0  # Continuous gradient
        
        # Atmospheric density decrease with altitude
        atmo = AtmosphericField()
        rho_ground = atmo.get_density(0.0)
        rho_high = atmo.get_density(5000.0)
        assert rho_ground > rho_high > 0.0
        
        # Resource field sampling
        res = ResourceField(size_x=50.0, size_y=50.0, grid_res=25)
        conc = res.sample_concentration(0.0, 0.0)
        assert 0.0 <= conc <= 100.0

    def test_03_organism_creation(self):
        """TEST 3: Organism creation and attribute modification."""
        org = OrganismTemplateLibrary.create_hexapod_forager("TEST_ORG", 5.0, -2.0, 1.0)
        assert org.id == "TEST_ORG"
        assert org.morphology.num_appendages == 6
        assert org.physiology.mass == 14.0
        assert org.is_alive is True
        
        # Modify supported attribute
        org.physiology.energy = 500.0
        assert org.physiology.energy == 500.0

    def test_04_sensor_output(self):
        """TEST 4: Sensor output consistent with physical models."""
        terrain = PlanetaryTerrain(size_x=50.0, size_y=50.0, grid_res=32)
        lidar = ProximityRaycastSensor(num_rays=5, max_range=10.0, noise_std=0.01)
        res = lidar.read(np.array([0.0, 0.0, 2.0]), heading=0.0, terrain=terrain)
        
        assert len(res["distances"]) == 5
        assert 0.0 <= res["min_distance"] <= 10.0
        
        # Chemical sensor reading
        r_field = ResourceField(size_x=50.0, size_y=50.0, grid_res=25)
        chem = ChemicalGradientSensor(baseline_noise_std=0.02)
        c_read = chem.read(np.array([0.0, 0.0, 0.0]), heading=0.0, resource_field=r_field)
        assert "concentration_center" in c_read
        assert "lateral_gradient" in c_read

    def test_05_controller_response(self):
        """TEST 5: Changing sensor input produces observable controller response."""
        fsm = FSMController(obstacle_clearance_m=2.0)
        
        # Clear field -> WANDER
        act_clear, _ = fsm.step(0.0, energy_j=1000.0, lidar_data={"min_distance": 8.0}, chemical_data={"detected": False})
        assert fsm.current_state == "WANDER"
        
        # Obstacle near -> AVOID_OBSTACLE
        act_obs, _ = fsm.step(0.0, energy_j=1000.0, lidar_data={"min_distance": 1.2}, chemical_data={"detected": False})
        assert fsm.current_state == "AVOID_OBSTACLE"
        assert act_obs["steering"] > 1.0  # Turning away
        
        # Chemical scent detected -> FORAGE
        act_forage, _ = fsm.step(0.0, energy_j=1000.0, lidar_data={"min_distance": 6.0}, chemical_data={"detected": True, "lateral_gradient": 0.5})
        assert fsm.current_state == "FORAGE"
        assert act_forage["throttle"] > 5.0

    def test_06_movement_and_physics(self):
        """TEST 6: Actions update organism position and velocity via physics."""
        terrain = PlanetaryTerrain(size_x=50.0, size_y=50.0, grid_res=32)
        atmo = AtmosphericField()
        physics = PhysicsSimulator(terrain, atmo)
        
        pos = np.array([0.0, 0.0, 1.0])
        vel = np.array([0.0, 0.0, 0.0])
        heading = 0.0
        
        # Throttle forward
        new_pos, new_vel, new_heading = physics.step_organism_kinematics(
            pos, vel, heading, throttle=10.0, steering=0.0, mass=10.0, dt=0.05
        )
        assert new_pos[0] > pos[0]  # Moved in x direction
        assert new_vel[0] > 0.0

    def test_07_animation_kinematics(self):
        """TEST 7: Visual movement corresponds to simulation state."""
        org = OrganismTemplateLibrary.create_hexapod_forager("ANIM_ORG", 0.0, 0.0, 0.5)
        terrain = PlanetaryTerrain(size_x=50.0, size_y=50.0, grid_res=32)
        gait = GaitGenerator()
        
        feet = gait.evaluate_feet_targets(org, terrain, time_sec=0.5)
        assert len(feet) == 6
        for leg in feet:
            assert "hip" in leg and "knee" in leg and "foot" in leg
            assert leg["foot"][2] >= terrain.get_elevation(leg["foot"][0], leg["foot"][1]) - 0.05

    def test_08_processor_constraints(self):
        """TEST 8: Changing virtual compute budget produces measurable latency change."""
        vcpu = VirtualMicroprocessor(clock_frequency_hz=100.0)
        instructions = {"ARITHMETIC": 50, "LOGIC_BRANCH": 25, "SENSOR_READ": 10}
        
        # Low clock (100 Hz)
        res_low = vcpu.execute_routine(instructions, simulation_step_dt=0.02)
        latency_low = res_low["simulated_latency_sec"]
        
        # High clock (25,000 Hz / 25 kHz)
        vcpu.set_clock_frequency(25000.0)
        res_high = vcpu.execute_routine(instructions, simulation_step_dt=0.02)
        latency_high = res_high["simulated_latency_sec"]
        
        assert latency_low > latency_high
        assert res_high["deadline_met"] is True

    def test_09_repeatability(self):
        """TEST 9: Repeated runs with identical seed produce identical state trajectories."""
        def run_sim(seed_val):
            sim = SimulationOrchestrator(seed=seed_val)
            sim.spawn_organism(x=0.0, y=0.0)
            for _ in range(50):
                sim.step(dt=0.02)
            return (sim.organisms[0].pos.copy(), sim.organisms[0].physiology.energy)
            
        pos1, energy1 = run_sim(12345)
        pos2, energy2 = run_sim(12345)
        
        assert np.allclose(pos1, pos2, atol=1e-6)
        assert abs(energy1 - energy2) < 1e-6

    def test_10_experiment_logging(self):
        """TEST 10: Experiment metrics, energy ledgers, and telemetry logged to disk."""
        sim = SimulationOrchestrator(seed=42)
        sim.spawn_organism(x=0.0, y=0.0)
        for _ in range(20):
            sim.step(dt=0.02)
            
        assert len(sim.telemetry_records) > 0
        rec = sim.telemetry_records[0]
        assert "energy_j" in rec
        assert "fsm_state" in rec
        assert "time_sec" in rec

    def test_11_failure_handling(self):
        """TEST 11: Invalid inputs handled gracefully without process crash."""
        terrain = PlanetaryTerrain(size_x=50.0, size_y=50.0, grid_res=32)
        # Coordinate outside terrain boundary clamped safely
        elev = terrain.get_elevation(9999.0, -9999.0)
        assert not np.isnan(elev)
        
        # Negative energy clamped and flagged
        budget = org = OrganismTemplateLibrary.create_hexapod_forager("STARVE_ORG", 0.0, 0.0, 1.0)
        org.physiology.energy = -500.0
        alive = org.physiology.step_metabolism(speed=5.0, dt=1.0)
        assert org.physiology.energy == 0.0

    def test_12_documentation(self):
        """TEST 12: Documentation files exist and match requirements."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        expected_docs = [
            "LEVEL_2_MASTER_PLAN.md",
            "LEVEL_2_ARCHITECTURE.md",
            "LEVEL_2_VOLUME_INDEX.md",
            "LEVEL_2_REQUIREMENTS.md",
            "LEVEL_2_EXPERIMENTAL_PROTOCOL.md",
            "LEVEL_2_SCIENTIFIC_LIMITATIONS.md",
            "LEVEL_2_IMPLEMENTATION_STATUS.md"
        ]
        for doc in expected_docs:
            p = os.path.join(repo_root, doc)
            assert os.path.exists(p), f"Missing required document: {doc}"

    def test_13_pdf_volume_index_validation(self):
        """TEST 13: All 40 volume specifications defined in research index."""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        index_path = os.path.join(repo_root, "LEVEL_2_VOLUME_INDEX.md")
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
        for i in range(1, 41):
            assert f"VOL-{i:02d}" in content

    def test_14_end_to_end_integration(self):
        """TEST 14: Complete integrated vertical slice simulation executes cleanly."""
        sim = SimulationOrchestrator(seed=99)
        org1 = sim.spawn_organism("Hexapod_Forager", x=-10.0, y=-10.0)
        org2 = sim.spawn_organism("Aquatic_Serpentine", x=10.0, y=10.0)
        
        # Execute 100 simulation steps
        for _ in range(100):
            sim.step(dt=0.02)
            
        assert sim.step_count == 100
        assert sim.simulation_time > 1.9
        assert len(org1.trajectory_history) > 5
        assert len(org2.trajectory_history) > 5
        
        # Test 3D scene construction
        fig = Visual3DStudio.build_scene_figure(sim.terrain, sim.organisms, sim.resource_field)
        assert fig is not None
        assert len(fig.data) >= 3  # Terrain + organisms + markers
