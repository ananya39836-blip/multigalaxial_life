"""
level_2/animation.py - Procedural Rigging, Inverse Kinematics, Gaits & 3D WebGL Viewport
Part VI: Controllable 3D Animation and Movement
"""

import math
import numpy as np
import plotly.graph_objects as go
from typing import List, Dict, Any, Tuple
from level_2.organisms import Organism
from level_2.environment import PlanetaryTerrain, ResourceField


class ProceduralIK:
    """
    Analytical 2-bone Inverse Kinematics (femur-tibia) solver.
    Computes hip angle and knee joint flex to place foot target on terrain.
    """
    @staticmethod
    def solve_2bone(
        hip_pos: np.ndarray,
        target_pos: np.ndarray,
        l1: float = 0.35,
        l2: float = 0.40
    ) -> Tuple[np.ndarray, bool]:
        """
        Returns (knee_pos, is_reachable).
        """
        d_vec = target_pos - hip_pos
        dist = np.linalg.norm(d_vec)
        
        # Max reach clamp
        max_reach = (l1 + l2) * 0.99
        if dist > max_reach:
            target_pos = hip_pos + (d_vec / dist) * max_reach
            dist = max_reach
            
        min_reach = abs(l1 - l2) * 1.01
        dist = max(min_reach, dist)
        
        # Cosine rule for knee angle
        cos_knee = (l1**2 + l2**2 - dist**2) / (2.0 * l1 * l2)
        cos_knee = np.clip(cos_knee, -1.0, 1.0)
        
        # Midpoint construction
        mid_dir = d_vec / dist
        up_vec = np.array([0.0, 0.0, 1.0])
        knee_normal = np.cross(mid_dir, up_vec)
        if np.linalg.norm(knee_normal) < 1e-4:
            knee_normal = np.array([1.0, 0.0, 0.0])
        else:
            knee_normal = knee_normal / np.linalg.norm(knee_normal)
            
        a = (l1**2 - l2**2 + dist**2) / (2.0 * dist)
        h = math.sqrt(max(0.0, l1**2 - a**2))
        
        knee_pos = hip_pos + a * mid_dir + h * np.array([0.0, 0.0, 0.5])
        return knee_pos, True


class GaitGenerator:
    """
    Generates phase-coordinated multi-legged wave and tripod gaits.
    """
    def __init__(self, step_freq_hz: float = 2.0, stride_length: float = 0.45, step_height: float = 0.25):
        self.freq = float(step_freq_hz)
        self.stride = float(stride_length)
        self.height = float(step_height)

    def evaluate_feet_targets(
        self,
        organism: Organism,
        terrain: PlanetaryTerrain,
        time_sec: float
    ) -> List[Dict[str, np.ndarray]]:
        """
        Computes world-space foot targets and knee joints for all limbs.
        """
        speed = float(np.linalg.norm(organism.vel[:2]))
        omega = 2.0 * math.pi * self.freq * max(0.2, min(2.5, speed))
        
        results = []
        heading = organism.heading
        fwd = np.array([math.cos(heading), math.sin(heading), 0.0])
        right = np.array([-math.sin(heading), math.cos(heading), 0.0])
        
        for limb in organism.morphology.limbs:
            phase = (time_sec * omega + limb["phase_offset"]) % (2.0 * math.pi)
            is_stance = phase < math.pi
            
            # Hip origin on body segment
            seg_idx = limb["segment_index"]
            seg_offset = organism.morphology.segment_offsets[seg_idx]
            hip_pos = organism.pos + seg_offset * fwd + limb["side"] * (organism.morphology.width / 2.0) * right
            
            # Ground foot target
            cycle_progress = math.sin(phase)
            lift = self.height * max(0.0, cycle_progress) if not is_stance else 0.0
            
            stride_offset = (math.cos(phase) * self.stride) * fwd
            neutral_foot = hip_pos + limb["side"] * 0.4 * right + stride_offset
            
            ground_z = terrain.get_elevation(neutral_foot[0], neutral_foot[1])
            foot_pos = np.array([neutral_foot[0], neutral_foot[1], ground_z + lift])
            
            # Solve 2-bone IK
            knee_pos, _ = ProceduralIK.solve_2bone(hip_pos, foot_pos, limb["femur_len"], limb["tibia_len"])
            
            results.append({
                "limb_id": limb["limb_id"],
                "hip": hip_pos,
                "knee": knee_pos,
                "foot": foot_pos,
                "is_stance": is_stance
            })
            
        return results


class Visual3DStudio:
    """
    Renders the complete 3D planetary ecosystem scene in WebGL (via Plotly 3D).
    Supports multi-agent rendering, sensor ray visualizers, terrain surfaces,
    and camera perspective switching (Orbit, Chase, First-Person).
    """
    @staticmethod
    def build_scene_figure(
        terrain: PlanetaryTerrain,
        organisms: List[Organism],
        resource_field: Optional[ResourceField] = None,
        camera_mode: str = "Chase",
        selected_organism_id: Optional[str] = None,
        time_sec: float = 0.0,
        subsample: int = 2
    ) -> go.Figure:
        """Constructs an interactive 3D WebGL figure."""
        fig = go.Figure()
        
        # 1. 3D Terrain Surface
        # Subsample grid for interactive rendering
        res = terrain.grid_res
        step = max(1, subsample)
        x_vals = np.linspace(-terrain.size_x / 2.0, terrain.size_x / 2.0, res)[::step]
        y_vals = np.linspace(-terrain.size_y / 2.0, terrain.size_y / 2.0, res)[::step]
        z_vals = terrain.heightfield[::step, ::step]
        
        fig.add_trace(go.Surface(
            x=x_vals,
            y=y_vals,
            z=z_vals,
            colorscale="Viridis",
            cmin=-8.0,
            cmax=12.0,
            showscale=False,
            opacity=0.88,
            hoverinfo="none",
            name="Planetary Terrain"
        ))
        
        # 2. Resource Blooms (Heatmap scatter overlay on ground)
        if resource_field:
            rx = np.linspace(-resource_field.size_x / 2.0, resource_field.size_x / 2.0, resource_field.res)[::3]
            ry = np.linspace(-resource_field.size_y / 2.0, resource_field.size_y / 2.0, resource_field.res)[::3]
            r_xx, r_yy = np.meshgrid(rx, ry)
            r_grid = resource_field.grid[::3, ::3]
            
            mask = r_grid > 20.0
            if np.any(mask):
                px = r_xx[mask]
                py = r_yy[mask]
                pz = [terrain.get_elevation(px[i], py[i]) + 0.1 for i in range(len(px))]
                p_intensities = r_grid[mask]
                
                fig.add_trace(go.Scatter3d(
                    x=px, y=py, z=pz,
                    mode="markers",
                    marker=dict(size=4, color=p_intensities, colorscale="YlGn", opacity=0.7),
                    name="Nutrient Fields",
                    hoverinfo="text",
                    text=[f"Nutrient: {v:.1f} J" for v in p_intensities]
                ))
        
        # 3. Organisms & Articulated Appendages
        gait = GaitGenerator()
        primary_org = None
        
        for org in organisms:
            if not org.is_alive:
                continue
                
            if org.id == selected_organism_id or primary_org is None:
                primary_org = org
                
            # Organism body core
            fig.add_trace(go.Scatter3d(
                x=[org.pos[0]], y=[org.pos[1]], z=[org.pos[2]],
                mode="markers+text",
                marker=dict(size=9, color=f"rgb{org.morphology.color}", symbol="diamond"),
                text=[f"#{org.id} [{org.fsm_state}]"],
                textposition="top center",
                name=f"Organism {org.id}"
            ))
            
            # Directional Heading Pointer
            h = org.heading
            dir_len = 1.6
            hx = [org.pos[0], org.pos[0] + dir_len * math.cos(h)]
            hy = [org.pos[1], org.pos[1] + dir_len * math.sin(h)]
            hz = [org.pos[2], org.pos[2]]
            fig.add_trace(go.Scatter3d(
                x=hx, y=hy, z=hz,
                mode="lines",
                line=dict(color="cyan", width=5),
                showlegend=False,
                hoverinfo="none"
            ))
            
            # Articulated Limb Segments via Inverse Kinematics
            limb_data = gait.evaluate_feet_targets(org, terrain, time_sec)
            for leg in limb_data:
                lx = [leg["hip"][0], leg["knee"][0], leg["foot"][0]]
                ly = [leg["hip"][1], leg["knee"][1], leg["foot"][1]]
                lz = [leg["hip"][2], leg["knee"][2], leg["foot"][2]]
                
                color = "white" if leg["is_stance"] else "orange"
                fig.add_trace(go.Scatter3d(
                    x=lx, y=ly, z=lz,
                    mode="lines+markers",
                    line=dict(color=color, width=3),
                    marker=dict(size=3, color=color),
                    showlegend=False,
                    hoverinfo="none"
                ))
                
            # Sensor Raycast Overlay (if selected)
            if org.id == selected_organism_id and "lidar_front" in org.sensor_readings:
                lidar = org.sensor_readings["lidar_front"]
                for ep in lidar.get("endpoints", []):
                    rx = [org.pos[0], ep[0]]
                    ry = [org.pos[1], ep[1]]
                    rz = [org.pos[2], terrain.get_elevation(ep[0], ep[1])]
                    fig.add_trace(go.Scatter3d(
                        x=rx, y=ry, z=rz,
                        mode="lines",
                        line=dict(color="rgba(255, 50, 50, 0.5)", width=2),
                        showlegend=False,
                        hoverinfo="none"
                    ))

        # 4. Camera Setup based on selected perspective
        cam_target = dict(x=0, y=0, z=0)
        cam_eye = dict(x=1.3, y=1.3, z=1.2)
        
        if primary_org:
            px, py, pz = primary_org.pos
            ph = primary_org.heading
            
            if camera_mode == "Chase":  # Third-person chase camera behind organism
                dist_back = 6.0
                elev = 3.5
                cam_eye = dict(
                    x=(px - dist_back * math.cos(ph)) / terrain.size_x * 2.0,
                    y=(py - dist_back * math.sin(ph)) / terrain.size_y * 2.0,
                    z=(pz + elev) / 20.0
                )
                cam_target = dict(x=px / terrain.size_x * 2.0, y=py / terrain.size_y * 2.0, z=pz / 20.0)
            elif camera_mode == "FirstPerson":  # Organism sensor viewpoint
                fwd_look = 8.0
                cam_eye = dict(
                    x=px / terrain.size_x * 2.0,
                    y=py / terrain.size_y * 2.0,
                    z=(pz + 0.5) / 20.0
                )
                cam_target = dict(
                    x=(px + fwd_look * math.cos(ph)) / terrain.size_x * 2.0,
                    y=(py + fwd_look * math.sin(ph)) / terrain.size_y * 2.0,
                    z=pz / 20.0
                )
            else:  # Orbit / Top-down overview
                cam_eye = dict(x=1.4, y=1.4, z=1.3)
                cam_target = dict(x=0, y=0, z=0)
                
        fig.update_layout(
            scene=dict(
                xaxis=dict(title="X (m)", showgrid=True, zeroline=False, backgroundcolor="#080c18"),
                yaxis=dict(title="Y (m)", showgrid=True, zeroline=False, backgroundcolor="#080c18"),
                zaxis=dict(title="Elevation Z (m)", showgrid=True, zeroline=False, backgroundcolor="#080c18"),
                camera=dict(eye=cam_eye, center=cam_target),
                aspectratio=dict(x=1.5, y=1.5, z=0.45)
            ),
            margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="#060913",
            font=dict(color="#94a3b8")
        )
        return fig
