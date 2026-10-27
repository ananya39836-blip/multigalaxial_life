# MULTIGALAXIAL LIFE — LEVEL 2: SYSTEM ARCHITECTURE SPECIFICATION

### 1. Architectural Philosophy
The Level 2 simulation engine is engineered around the principle of **strict sensorimotor decoupling**:
- The **Environment** knows nothing about organism intentions; it merely computes terrain elevations, fluid drag, gravitational acceleration, and thermodynamic dissipation.
- The **Organism** possesses no global knowledge of the world; its internal state updates solely via local **Sensors**.
- The **Virtual Processor** enforces computational latency and cycle budgets between raw sensor readings and controller execution.
- The **Visualization Layer** is an observer that consumes world states without mutating simulation physics.

---

### 2. High-Level Subsystem Breakdown

#### Subsystem A: Environment Engine (`level_2.environment`)
- `PlanetaryTerrain`: Generates 2.5D height fields $z = h(x, y)$ using multi-octave Perlin/Simplex noise, thermal erosion filters, and crater impact morphology.
- `AtmosphericField`: Computes pressure profiles $P(z) = P_0 \exp(-z / H)$, local ambient temperature $T(x, y, z)$, dynamic viscosity $\mu$, and solar radiation vectors.
- `ResourceField`: 2D spatial density distributions for nutrients $S_{nut}(x, y)$, water/volatiles $S_{wat}(x, y)$, and environmental hazards $S_{haz}(x, y)$ with logistic diffusion and regeneration dynamics:
  $$\frac{\partial S}{\partial t} = D \nabla^2 S + r S \left(1 - \frac{S}{K}\right) - \sum_{i} \dot{C}_i(\mathbf{x}, t)$$
- `PhysicsEngine`: Semi-implicit Euler integration of rigid body kinematics, terrain collision detection, normal reaction forces, surface Coulomb friction ($\mu_s, \mu_k$), and buoyancy approximations.

#### Subsystem B: Organism Engine (`level_2.organisms`)
- `MorphologyModel`: Articulated kinematic graph comprising root base, body segments, actuated appendages, joint angle bounds $[\theta_{min}, \theta_{max}]$, and mass distribution.
- `PhysiologicalBudget`: Thermodynamic energy balance:
  $$\frac{dE}{dt} = \dot{E}_{ingest} - \dot{E}_{basal} - \dot{E}_{locomotion} - \dot{E}_{compute} - \dot{E}_{sensor}$$
- `LifecycleState`: Age $\tau$, metabolic health $H \in [0, 1]$, reproduction threshold $E > E_{repr}$, and somatic death criteria ($E \le 0$ or $H \le 0$).

#### Subsystem C: Sensor Engine (`level_2.sensors`)
- `VirtualCamera`: 2D rendering buffer with configurable focal length $f$, field of view $\text{FOV}$, Gaussian lens blur, and sensor readout noise.
- `DepthSensor`: 1D/2D z-buffer depth map with range quantization and distance dropouts.
- `ProximityRaycaster`: Multi-ray spherical lidar rangefinder detecting terrain distance and obstacle intersections.
- `ChemicalSensor`: Point sampling of scalar resource fields with diffusion noise and detection thresholds:
  $$c_{meas} = \max(0, c_{true} + \mathcal{N}(0, \sigma_{chem}^2))$$
- `InertialMeasurementUnit (IMU)`: 3-axis accelerometer and rate gyroscope with bias drift and Allan variance noise.

#### Subsystem D: Controller Engine (`level_2.controllers`)
- `FSMController`: Discrete states (e.g., `FORAGE`, `AVOID_OBSTACLE`, `REST_METABOLIZE`, `REPRODUCE`, `FLEE_HAZARD`) with deterministic transition guards.
- `BehaviorTreeController`: Hierarchical execution graph with Selector, Sequence, Parallel, and Action nodes.
- `PIDController`: Continuous closed-loop heading and velocity tracking:
  $$u(t) = K_p e(t) + K_i \int_0^t e(\tau)\,d\tau + K_d \frac{de(t)}{dt}$$

#### Subsystem E: Virtual Microprocessor (`level_2.processors`)
- `VirtualCPU`: Models simulated execution cycles $f_{clk} \in [10^3, 10^7]\,\text{Hz}$, instruction set architecture (ISA) weights, working memory capacity $M_{words}$, instruction queue buffers, and scheduling delays.
- `EnergyAccounting`: Tracks simulated computation energy $\dot{E}_{cpu} = \alpha_{cpu} f_{clk} + \beta_{inst} N_{ops}$.
- *Explicit Limitation Notice: All cycles, latencies, and instruction counts are simulated software models and do not represent physical hardware execution.*

#### Subsystem F: Animation & Kinematics Engine (`level_2.animation`)
- `ProceduralIK`: 2-bone and multi-joint analytical and Jacobian-transpose Inverse Kinematics ensuring feet maintain non-penetrating terrain contact.
- `GaitGenerator`: Wave gaits, tripod gaits, and serpentine swimming undulations parameterized by phase frequency $\omega$ and stride length.
- `Viewport3D`: WebGL and Plotly 3D interactive mesh rendering supporting dynamic camera control (Orbit, Third-Person Chase, First-Person Sensor POV).

#### Subsystem G: Experimentation & Logging (`level_2.experiments`)
- `ExperimentRunner`: Coordinates repeated Monte Carlo trials with seeded pseudo-random number generators (PRNG), parameter sweeps, and ablation testing.
- `MetricsLogger`: Real-time telemetry recording of population censuses, individual trajectories, energy time-series, and controller state distributions.
- `CheckpointManager`: Full deterministic snapshot serialization (JSON/HDF5) enabling exact simulation replay.

---

### 3. Pipeline Dataflow & Execution Loop

```text
[Simulation Clock Tick (dt)]
   │
   ├─► 1. Environment: Update resource diffusion and atmospheric wind fields
   │
   ├─► 2. Sensor Engine: Raycast terrain, sample chemical fields, capture camera frames
   │
   ├─► 3. Virtual CPU: Buffer raw sensor packets, apply cycle cost and scheduling latency
   │
   ├─► 4. Controller Engine: Execute active FSM / Behavior Tree / PID control logic
   │
   ├─► 5. Organism Engine: Deduct metabolic costs, check somatic health and lifecycle rules
   │
   ├─► 6. Physics Engine: Apply actuator forces, resolve rigid collisions and friction
   │
   ├─► 7. Animation Engine: Update skeletal joint matrices and procedural gaits
   │
   ├─► 8. Telemetry Logger: Buffer state vectors, verify conservation laws, append logs
   │
   └─► 9. Viewport Engine: Render interactive 3D frame (sub-sampled if rendering < physics dt)
```
