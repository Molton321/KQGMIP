"""KGeoMIP — geometric strategy extended to k-partitions.

This strategy generalizes GeoMIP (the geometric/dynamic-programming bipartition
method) to k-partitions with k ∈ {2..5}, following the official specification
``docs/Proyecto_KQMIP.md``:

- §2.2/§2.3: a k-partition corresponds to dividing the hypercube with **k−1
  hyperplanes**, equivalently to applying **k−1 successive bipartitions**
  (greedy; global optimality is not guaranteed).
- §2.3/§3: the transition-cost table ``T`` is the expensive shared structure and
  must be **computed once and reused for every k**.
- §2.1: a k-partition has exactly k genuine (non-vacuous) parts.

KGeoMIP builds ``T`` once (:class:`CostTable`) and performs greedy hierarchical
refinement: starting from the whole subsystem as a single block, it repeatedly
splits one block with the geometric cut (projected from ``T``'s bipartition
candidates) that minimizes the k-generic loss ``delta_k``, until k non-vacuous
blocks are reached. For k=2 the search reduces to a single geometric cut and
therefore reproduces GeoMIP exactly.
"""

import time

import numpy as np

from src.constants.base import COLS_IDX, NET_LABEL, TYPE_TAG
from src.funcs.cost_table import CostTable
from src.funcs.emd import delta_k
from src.funcs.format import fmt_kpartition
from src.middlewares.profile import profile, profiling_manager
from src.middlewares.slogger import SafeLogger
from src.models.base.application import application
from src.models.base.sia import SIA
from src.models.core.partition import KPartition
from src.models.core.solution import Solution

KGEOMIP_LABEL: str = "KGeoMIP"
KGEOMIP_STRATEGY_TAG: str = f"{KGEOMIP_LABEL}_strategy"
KGEOMIP_ANALYSIS_TAG: str = f"{KGEOMIP_LABEL}_analysis"

# A block pairs a set of future (purview) indices with a set of present
# (mechanism) indices. A block is non-vacuous when either set is non-empty.
Block = tuple[frozenset[int], frozenset[int]]


class KGeoMIP(SIA):
    """Geometric k-partition strategy (k ∈ {2..5}) reusing the cost table T."""

    def __init__(self, tpm: np.ndarray, initial_state: str, k: int) -> None:
        super().__init__(tpm, initial_state)
        profiling_manager.start_session(
            f"{NET_LABEL}{len(tpm[COLS_IDX])}{application.sample_network_page}"
        )
        self.logger = SafeLogger(KGEOMIP_STRATEGY_TAG)
        self.k = k
        self.cost_table: CostTable
        self.best_partition: KPartition | None = None

    @profile(context={TYPE_TAG: KGEOMIP_ANALYSIS_TAG})
    def apply_strategy(self, condition: str, purview: str, mechanism: str) -> Solution:
        """Search for a low-loss k-partition under the current subsystem."""
        self.sia_prepare_subsystem(condition, purview, mechanism)

        if self.k < 2:
            raise ValueError("k must be >= 2.")

        subsystem = self.sia_subsystem
        baseline = self.sia_marginal_dists

        future_universe = tuple(int(i) for i in subsystem.ncube_indices.tolist())
        present_universe = tuple(int(i) for i in subsystem.ncube_dims.tolist())

        # A strict k-partition needs at least k non-vacuous parts, so the number
        # of available atoms (future + present nodes) must be at least k.
        atoms = len(future_universe) + len(present_universe)
        if self.k > atoms:
            raise ValueError(
                f"k={self.k} exceeds the {atoms} available atoms "
                f"({len(future_universe)} future + {len(present_universe)} present)."
            )

        # Build the cost table T once; reused for every candidate (doc §3).
        self.cost_table = self._build_cost_table(subsystem)
        cut_pool = self._cut_pool(subsystem)

        self.sia_logger.critic("Iniciando búsqueda geométrica k-partita.")
        blocks: list[Block] = [(frozenset(future_universe), frozenset(present_universe))]
        while len(blocks) < self.k:
            refined = self._best_refinement(
                blocks, cut_pool, future_universe, present_universe, baseline
            )
            if refined is None:
                raise RuntimeError(
                    f"KGeoMIP could not refine into {self.k} non-vacuous blocks "
                    f"(stuck at {len(blocks)})."
                )
            blocks = refined

        partition = self._to_kpartition(blocks, future_universe, present_universe)
        loss, distribution = delta_k(subsystem, partition, baseline_distribution=baseline)
        self.best_partition = partition

        return Solution(
            strategy=f"{KGEOMIP_LABEL}(k={self.k})",
            loss=float(loss),
            subsystem_distribution=baseline,
            partition_distribution=distribution,
            total_time=time.time() - self.sia_start_time,
            partition=fmt_kpartition(partition.signature),
        )

    def _build_cost_table(self, subsystem) -> CostTable:
        """Construct the reusable Hamming-weighted transition-cost table T."""
        flat_data = [cube.data.ravel() for cube in subsystem.ncubes]
        state_start = subsystem.initial_state[subsystem.ncube_dims]
        state_end = 1 - state_start
        return CostTable(flat_data, state_start, state_end)

    def _cut_pool(self, subsystem) -> list[Block]:
        """Map the cost table's bipartition candidates to actual-index blocks.

        Each geometric candidate ``[present_positions, future_positions]`` is
        converted into the block ``(future_indices, present_indices)`` it
        selects, so it can be intersected with any sub-block during refinement.
        """
        dims = subsystem.ncube_dims
        indices = subsystem.ncube_indices
        pool: list[Block] = []
        for present_pos, future_pos in self.cost_table.candidate_bipartitions():
            effect_set = frozenset(int(x) for x in indices[future_pos])
            present_set = frozenset(int(x) for x in dims[present_pos])
            pool.append((effect_set, present_set))
        return pool

    def _best_refinement(
        self,
        blocks: list[Block],
        cut_pool: list[Block],
        future_universe: tuple[int, ...],
        present_universe: tuple[int, ...],
        baseline: np.ndarray,
    ) -> list[Block] | None:
        """Return the blocks after the single best (lowest δ_k) geometric split.

        Tries every (block, geometric cut) pairing that divides a block into two
        non-vacuous sub-blocks, scores the resulting full partition with
        ``delta_k``, and keeps the minimum. Returns ``None`` if no such split
        exists (no block can be divided into two non-vacuous parts).
        """
        best_loss = np.inf
        best_blocks: list[Block] | None = None

        for position, (effects_block, present_block) in enumerate(blocks):
            # A block needs at least two atoms to split into two non-vacuous parts.
            if len(effects_block) + len(present_block) < 2:
                continue

            for cut_effects, cut_present in cut_pool:
                inside: Block = (effects_block & cut_effects, present_block & cut_present)
                outside: Block = (effects_block - cut_effects, present_block - cut_present)

                # Reject splits that leave a fully empty (vacuous) side.
                if not (inside[0] or inside[1]) or not (outside[0] or outside[1]):
                    continue

                candidate_blocks = blocks[:position] + [inside, outside] + blocks[position + 1 :]
                partition = self._to_kpartition(
                    candidate_blocks, future_universe, present_universe
                )
                loss, _ = delta_k(self.sia_subsystem, partition, baseline_distribution=baseline)
                if loss < best_loss:
                    best_loss = loss
                    best_blocks = candidate_blocks

        return best_blocks

    @staticmethod
    def _to_kpartition(
        blocks: list[Block],
        future_universe: tuple[int, ...],
        present_universe: tuple[int, ...],
    ) -> KPartition:
        """Build a validated ``KPartition`` from the current working blocks."""
        return KPartition.from_blocks(
            blocks=[
                (tuple(sorted(effects)), tuple(sorted(present))) for effects, present in blocks
            ],
            future_universe=future_universe,
            present_universe=present_universe,
        )
