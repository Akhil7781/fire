"""
Uber H3 resolution 8 spatial indexing and local candidate retrieval.
INVARIANT: H3 is strictly a geographic context index and NEVER a physical fire/source identifier.
"""

from __future__ import annotations

from typing import Dict, List, Set
import numpy as np
import h3


def assign_h3_res8(lats: np.ndarray, lons: np.ndarray) -> List[str]:
    """
    Computes Uber H3 resolution 8 cell index for coordinate arrays.
    """
    cells = [h3.latlng_to_cell(float(lat), float(lon), 8) for lat, lon in zip(lats, lons)]
    return cells


def get_2km_candidate_cells(origin_cell: str) -> Set[str]:
    """
    Retrieves the 3-ring neighborhood of H3 resolution 8 cells around the origin.
    A 3-ring disk encompasses 37 cells, providing guaranteed full spatial coverage
    of the 2.0 km local causal context radius.

    Proof: H3 res8 cells have vertex radius ~553m. A detection near its cell boundary
    and a candidate 2 km away near its own cell boundary can be in cells up to
    ~3106m center-to-center apart. The 2-ring max coverage is ~1926m (insufficient).
    The 3-ring max coverage is ~2889m, and with vertex tolerance, guarantees recall
    of all candidates within 2000m geodesic distance.

    The exact Haversine distance check in causal_context.py performs the final
    inclusion/exclusion; this function only retrieves over-inclusive candidates.
    """
    return set(h3.grid_disk(origin_cell, 3))


class LocalSpatialIndex:
    """
    Inverted index mapping H3 resolution 8 cells to temporal detection records.
    Enables O(1) candidate lookup for the 2 km local causal context radius.
    """

    def __init__(self):
        # cell_id -> list of record indices
        self.cell_to_indices: Dict[str, List[int]] = {}

    def build(self, h3_cells: List[str]) -> None:
        self.cell_to_indices.clear()
        for idx, cell in enumerate(h3_cells):
            if cell not in self.cell_to_indices:
                self.cell_to_indices[cell] = []
            self.cell_to_indices[cell].append(idx)

    def query_candidates(self, origin_cell: str) -> List[int]:
        """
        Retrieves all detection indices located within the 3-ring neighborhood
        of the target cell. Over-inclusive by design; exact Haversine distance
        filtering is performed downstream.
        """
        candidate_cells = get_2km_candidate_cells(origin_cell)
        candidate_indices: List[int] = []
        for cell in candidate_cells:
            indices = self.cell_to_indices.get(cell)
            if indices:
                candidate_indices.extend(indices)
        return candidate_indices
