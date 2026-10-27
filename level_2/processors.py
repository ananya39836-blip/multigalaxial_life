"""
level_2/processors.py - Virtual Microprocessor & Computational Budget Simulation
Part V: Controllers, Microprocessors, and Embedded Systems

DISCLAIMER: This module provides an abstract software simulation of a virtual processor
with configurable cycle costs, memory constraints, and scheduling latency.
It does NOT represent or benchmark physical semiconductor hardware.
"""

import time
from typing import Dict, Any, List, Optional


class VirtualMicroprocessor:
    """
    Simulated RISC-like embedded processor.
    Exposes configurable clock rates, instruction cycle costs, memory limits,
    execution queue latency, and computational energy dissipation.
    """
    def __init__(
        self,
        processor_id: str = "vCPU_RISC_32",
        clock_frequency_hz: float = 500.0,
        memory_capacity_words: int = 1024,
        max_queue_depth: int = 16,
        energy_per_cycle_nj: float = 1.5
    ):
        self.id = processor_id
        self.clock_hz = float(clock_frequency_hz)
        self.memory_words = int(memory_capacity_words)
        self.max_queue = int(max_queue_depth)
        self.energy_per_cycle = float(energy_per_cycle_nj) * 1e-9  # Joules / cycle
        
        # Instruction cycle costs
        self.isa_costs = {
            "SENSOR_READ": 12,     # Memory-mapped peripheral I/O
            "ARITHMETIC": 2,       # ALU addition/multiplication
            "LOGIC_BRANCH": 3,     # Comparison and conditional branch
            "STATE_TRANSITION": 8, # Register spill & context update
            "MOTOR_COMMAND": 10    # PWM timer register write
        }
        
        # Runtime counters
        self.total_cycles_executed = 0
        self.total_instructions_executed = 0
        self.missed_deadlines = 0
        self.current_queue_depth = 0
        self.simulated_latency_sec = 0.0
        self.total_compute_energy_j = 0.0

    def execute_routine(
        self,
        instruction_counts: Dict[str, int],
        simulation_step_dt: float = 0.02
    ) -> Dict[str, Any]:
        """
        Simulates execution of a controller decision cycle.
        Computes required cycles, simulated latency, energy cost, and deadline compliance.
        """
        cycles_needed = 0
        total_ops = 0
        
        for op_type, count in instruction_counts.items():
            unit_cost = self.isa_costs.get(op_type, 4)
            cycles_needed += unit_cost * count
            total_ops += count
            
        # Simulated latency tau = cycles / clock_hz
        simulated_delay = cycles_needed / max(1.0, self.clock_hz)
        self.simulated_latency_sec = simulated_delay
        
        # Deadline check: Did execution exceed the physics time step?
        missed = simulated_delay > simulation_step_dt
        if missed:
            self.missed_deadlines += 1
            
        # Update metrics
        self.total_cycles_executed += cycles_needed
        self.total_instructions_executed += total_ops
        
        step_energy_j = cycles_needed * self.energy_per_cycle
        self.total_compute_energy_j += step_energy_j
        
        return {
            "processor_id": self.id,
            "cycles_executed": cycles_needed,
            "simulated_latency_sec": simulated_delay,
            "simulated_clock_hz": self.clock_hz,
            "deadline_met": not missed,
            "missed_deadlines_total": self.missed_deadlines,
            "energy_consumed_j": step_energy_j,
            "total_energy_consumed_j": self.total_compute_energy_j,
            "disclaimer": "Simulated software processor model; not physical hardware."
        }

    def set_clock_frequency(self, new_clock_hz: float):
        """Allows real-time throttling of simulated compute capacity."""
        self.clock_hz = max(10.0, float(new_clock_hz))

    def reset_metrics(self):
        """Reset runtime counters."""
        self.total_cycles_executed = 0
        self.total_instructions_executed = 0
        self.missed_deadlines = 0
        self.total_compute_energy_j = 0.0
