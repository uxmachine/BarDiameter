"""Rhino Python MVP command for measuring rebar diameter from a mesh segment.

Usage in Rhino Python editor:
    import rhino_rebar_diameter_mvp as tool
    tool.run_mvp()
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple

from diameter_stats import equivalent_diameter_from_area, summarize_diameters


@dataclass
class Settings:
    station_spacing_mm: float = 25.0
    min_diameter_mm: float = 8.0
    max_diameter_mm: float = 40.0
    trim_fraction: float = 0.1
    low_confidence_invalid_ratio: float = 0.3


def _build_adjacency(topology_edges, topo_vertices, topo_vertex_count: int) -> Dict[int, List[Tuple[int, float]]]:
    adjacency: Dict[int, List[Tuple[int, float]]] = {i: [] for i in range(topo_vertex_count)}
    for edge_i in range(topology_edges.Count):
        tv0, tv1 = topology_edges.GetTopologyVertices(edge_i)
        p0 = topo_vertices[tv0]
        p1 = topo_vertices[tv1]
        w = p0.DistanceTo(p1)
        adjacency[tv0].append((tv1, w))
        adjacency[tv1].append((tv0, w))
    return adjacency


def _dijkstra_path(adjacency: Dict[int, List[Tuple[int, float]]], start: int, goal: int) -> List[int]:
    dist = {start: 0.0}
    prev = {}
    pq = [(0.0, start)]
    seen = set()

    while pq:
        d, u = heapq.heappop(pq)
        if u in seen:
            continue
        seen.add(u)
        if u == goal:
            break
        for v, w in adjacency.get(u, []):
            nd = d + w
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))

    if goal not in dist:
        return []

    path = [goal]
    cur = goal
    while cur != start:
        cur = prev[cur]
        path.append(cur)
    path.reverse()
    return path


def _polyline_length(points: Sequence) -> float:
    return sum(points[i - 1].DistanceTo(points[i]) for i in range(1, len(points)))


def _sample_along_polyline(points: Sequence, spacing_mm: float) -> List[Tuple[object, object]]:
    """Return list of (point, tangent_vector)."""
    if len(points) < 2:
        return []

    samples: List[Tuple[object, object]] = []
    total = _polyline_length(points)
    if total <= spacing_mm:
        tangent = points[-1] - points[0]
        tangent.Unitize()
        return [(points[len(points) // 2], tangent)]

    targets = [i * spacing_mm for i in range(int(total // spacing_mm) + 1)]
    if targets[-1] < total:
        targets.append(total)

    seg_start_idx = 0
    seg_start_s = 0.0
    for target_s in targets:
        while seg_start_idx < len(points) - 2:
            seg_len = points[seg_start_idx].DistanceTo(points[seg_start_idx + 1])
            if seg_start_s + seg_len >= target_s:
                break
            seg_start_s += seg_len
            seg_start_idx += 1

        p0 = points[seg_start_idx]
        p1 = points[seg_start_idx + 1]
        seg_len = p0.DistanceTo(p1)
        t = 0.0 if seg_len == 0 else (target_s - seg_start_s) / seg_len
        sample_pt = p0 + (p1 - p0) * t

        tangent = p1 - p0
        if not tangent.Unitize():
            continue
        samples.append((sample_pt, tangent))

    return samples


def _largest_closed_curve_area(intersection_curves, rg) -> Tuple[float, int]:
    """Return (largest_area, loop_count_above_half_largest)."""
    closed_areas = []
    for crv in intersection_curves:
        if not crv.IsClosed:
            continue
        amp = rg.AreaMassProperties.Compute(crv)
        if amp is None:
            continue
        closed_areas.append(abs(amp.Area))

    if not closed_areas:
        return 0.0, 0

    largest = max(closed_areas)
    similar = sum(1 for a in closed_areas if a >= largest * 0.5)
    return largest, similar


def _nearest_topology_vertex_index(topo_vertices, point) -> int:
    """Return nearest topology vertex index for Rhino versions with differing APIs."""
    # Rhino versions differ here: some expose ClosestTopologyVertex, others don't.
    if hasattr(topo_vertices, "ClosestTopologyVertex"):
        return topo_vertices.ClosestTopologyVertex(point)

    best_i = -1
    best_d2 = float("inf")
    for i in range(topo_vertices.Count):
        v = topo_vertices[i]
        dx = v.X - point.X
        dy = v.Y - point.Y
        dz = v.Z - point.Z
        d2 = dx * dx + dy * dy + dz * dz
        if d2 < best_d2:
            best_d2 = d2
            best_i = i

    if best_i < 0:
        raise RuntimeError("Failed to find nearest topology vertex.")
    return best_i


def run_mvp(settings: Settings | None = None):
    settings = settings or Settings()

    try:
        import Rhino.Geometry as rg
        import rhinoscriptsyntax as rs
    except ImportError as exc:
        raise RuntimeError("This script must run inside Rhino's Python environment.") from exc

    mesh_id = rs.GetObject("Select merged rebar mesh", rs.filter.mesh, preselect=True)
    if not mesh_id:
        return

    p_start = rs.GetPointOnMesh(mesh_id, "Pick first point on a single rebar")
    if p_start is None:
        return
    p_end = rs.GetPointOnMesh(mesh_id, "Pick second point on same rebar (100-500mm away)")
    if p_end is None:
        return

    mesh_obj = rs.coercemesh(mesh_id)
    if mesh_obj is None:
        print("Could not coerce selected object to mesh.")
        return

    topo = mesh_obj.TopologyVertices
    edges = mesh_obj.TopologyEdges

    start_tv = _nearest_topology_vertex_index(topo, p_start)
    end_tv = _nearest_topology_vertex_index(topo, p_end)

    adjacency = _build_adjacency(edges, topo, topo.Count)
    tv_path = _dijkstra_path(adjacency, start_tv, end_tv)
    if len(tv_path) < 2:
        print("Failed to compute path on mesh. Pick points again on same bar segment.")
        return

    path_points = [topo[i] for i in tv_path]
    samples = _sample_along_polyline(path_points, settings.station_spacing_mm)
    if not samples:
        print("Failed to create stations along path.")
        return

    valid_diameters = []
    invalid_reasons = {"no_closed_loop": 0, "multi_loop": 0, "out_of_range": 0}

    for sample_pt, tangent in samples:
        plane = rg.Plane(sample_pt, tangent)
        curves = rg.Intersect.Intersection.MeshPlane(mesh_obj, plane)
        if not curves:
            invalid_reasons["no_closed_loop"] += 1
            continue

        area, similar_loop_count = _largest_closed_curve_area(curves, rg)
        if area <= 0:
            invalid_reasons["no_closed_loop"] += 1
            continue
        if similar_loop_count > 1:
            invalid_reasons["multi_loop"] += 1
            continue

        d = equivalent_diameter_from_area(area)
        if d < settings.min_diameter_mm or d > settings.max_diameter_mm:
            invalid_reasons["out_of_range"] += 1
            continue

        valid_diameters.append(d)

    summary = summarize_diameters(
        valid_diameters,
        total_station_count=len(samples),
        trim_fraction=settings.trim_fraction,
        low_confidence_invalid_ratio=settings.low_confidence_invalid_ratio,
    )

    if math.isnan(summary.estimated_diameter_mm):
        print("No valid stations found. Try a cleaner bar segment.")
        return

    print("Estimated diameter: {:.2f} mm".format(summary.estimated_diameter_mm))
    print("Variability (IQR): {:.2f} mm".format(summary.iqr_mm))
    print("Valid stations: {} / {}".format(summary.valid_station_count, summary.total_station_count))
    print("Confidence: {}".format(summary.confidence))
    print("Invalid station breakdown: {}".format(invalid_reasons))

    if summary.confidence == "Low":
        print("Low confidence: likely fusion/crossing in selected window.")


if __name__ == "__main__":
    run_mvp()
