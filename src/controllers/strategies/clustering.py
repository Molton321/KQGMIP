"""Deterministic clustering baseline for k-partitions (Phase 5A).

This is the required comparative baseline of the official portfolio
(``docs/Proyecto_KQMIP.md``; precedent "Estrategia KM"). It treats the k-MIP as
a **graph-partitioning** problem: an affinity graph over the subsystem nodes is
built from their mutual behaviour, and it is cut into k blocks by spectral
clustering (graph Laplacian + k-means on the eigenvectors) or plain k-means.

The clustering only **proposes** the partition; its quality is always measured
with the k-generic loss ``delta_k`` (Phase 1), never with the clustering's
internal objective. The strategy is fully deterministic (fixed
``application.numpy_seed``) and the affinity is computed from a bounded sample of
TPM rows, so it scales to the largest grids (N25) in seconds.

The proposed partition is **node-aligned**: each node is assigned to one block
and contributes both its future (purview) and present (mechanism) atom to that
block, so a valid strict k-partition needs ``k ≤ n`` nodes.
"""

import time

import numpy as np
from numpy.typing import NDArray
from scipy.cluster.vq import kmeans2
from scipy.sparse.csgraph import laplacian

from src.constants.base import COLS_IDX, NET_LABEL, TYPE_TAG
from src.funcs.emd import delta_k
from src.funcs.format import fmt_kpartition
from src.middlewares.profile import profile, profiling_manager
from src.middlewares.slogger import SafeLogger
from src.models.base.application import application
from src.models.base.sia import SIA
from src.models.core.partition import KPartition
from src.models.core.solution import Solution

CLUSTERING_LABEL: str = "Clustering"
CLUSTERING_STRATEGY_TAG: str = f"{CLUSTERING_LABEL}_strategy"
CLUSTERING_ANALYSIS_TAG: str = f"{CLUSTERING_LABEL}_analysis"

# Upper bound on TPM rows sampled to build the affinity (keeps n=25 in seconds).
MAX_AFFINITY_SAMPLE: int = 4096


class ClusteringSIA(SIA):
    """Deterministic graph-clustering baseline for k-partitions (k ∈ {2..n})."""

    def __init__(
        self,
        tpm: np.ndarray,
        initial_state: str,
        k: int,
        method: str = "spectral",
    ) -> None:
        super().__init__(tpm, initial_state)
        profiling_manager.start_session(
            f"{NET_LABEL}{len(tpm[COLS_IDX])}{application.sample_network_page}"
        )
        self.logger = SafeLogger(CLUSTERING_STRATEGY_TAG)
        self.network_tpm = tpm
        self.k = k
        self.method = method
        self.best_partition: KPartition | None = None

    @profile(context={TYPE_TAG: CLUSTERING_ANALYSIS_TAG})
    def apply_strategy(self, condition: str, purview: str, mechanism: str) -> Solution:
        """Propose a k-partition by clustering the node affinity graph."""
        self.sia_prepare_subsystem(condition, purview, mechanism)

        if self.k < 2:
            raise ValueError("k must be >= 2.")

        subsystem = self.sia_subsystem
        baseline = self.sia_marginal_dists

        nodes = tuple(int(i) for i in subsystem.ncube_indices.tolist())
        future_universe = nodes
        present_universe = tuple(int(i) for i in subsystem.ncube_dims.tolist())

        if self.k > len(nodes):
            raise ValueError(
                f"node-aligned clustering needs k <= n; got k={self.k}, n={len(nodes)}."
            )

        features = self._node_features(nodes)
        labels = self._cluster(features, self.k)

        partition = self._labels_to_kpartition(
            nodes, labels, future_universe, present_universe
        )
        loss, distribution = delta_k(subsystem, partition, baseline_distribution=baseline)
        self.best_partition = partition

        return Solution(
            strategy=f"{CLUSTERING_LABEL}({self.method}, k={self.k})",
            loss=float(loss),
            subsystem_distribution=baseline,
            partition_distribution=distribution,
            total_time=time.time() - self.sia_start_time,
            partition=fmt_kpartition(partition.signature),
        )

    def _node_features(self, nodes: tuple[int, ...]) -> NDArray[np.float64]:
        """Binarized behaviour of each node over a deterministic TPM-row sample.

        Returns an ``(n, sample)`` matrix where row ``i`` is the 0/1 response of
        node ``nodes[i]`` across the sampled states. Two nodes that respond
        alike across states are considered similar.
        """
        n_rows = self.network_tpm.shape[0]
        rng = np.random.default_rng(application.numpy_seed)
        if n_rows > MAX_AFFINITY_SAMPLE:
            sample = np.sort(rng.choice(n_rows, MAX_AFFINITY_SAMPLE, replace=False))
        else:
            sample = np.arange(n_rows)

        columns = self.network_tpm[np.ix_(sample, np.asarray(nodes, dtype=np.intp))]
        return (columns > 0.5).astype(np.float64).T

    def _affinity(self, features: NDArray[np.float64]) -> NDArray[np.float64]:
        """Agreement-fraction affinity matrix W[i,j] ∈ [0, 1] between nodes."""
        sample_size = features.shape[1]
        agreement = (features @ features.T) + ((1 - features) @ (1 - features).T)
        weights = agreement / max(sample_size, 1)
        np.fill_diagonal(weights, 0.0)
        return weights

    def _cluster(self, features: NDArray[np.float64], k: int) -> NDArray[np.int64]:
        """Cluster nodes into k groups, deterministically.

        ``spectral`` cuts the affinity graph via the normalized Laplacian
        eigenvectors; ``kmeans`` clusters the raw node-behaviour features. A
        Fiedler-ordering split is used as a fallback whenever k-means collapses
        into fewer than k non-empty clusters, guaranteeing a valid k-partition.
        """
        weights = self._affinity(features)
        normalized_laplacian = laplacian(weights, normed=True)
        _eigenvalues, eigenvectors = np.linalg.eigh(normalized_laplacian)

        if self.method == "kmeans":
            data = features
        else:
            embedding = eigenvectors[:, :k]
            norms = np.linalg.norm(embedding, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            data = embedding / norms

        try:
            _, labels = kmeans2(
                data, k, seed=application.numpy_seed, minit="++", missing="raise"
            )
        except Exception:  # pragma: no cover - degenerate clustering -> fallback
            labels = None

        if labels is None or len(set(int(x) for x in labels)) < k:
            labels = self._fiedler_split(eigenvectors, k)
        return np.asarray(labels, dtype=np.int64)

    @staticmethod
    def _fiedler_split(eigenvectors: NDArray[np.float64], k: int) -> NDArray[np.int64]:
        """Split nodes into k non-empty groups by Fiedler-vector ordering.

        Sorts nodes along the second-smallest Laplacian eigenvector (the Fiedler
        vector) and cuts the ordering into k contiguous near-equal blocks. This
        always yields k non-empty groups when ``n >= k``.
        """
        fiedler_index = 1 if eigenvectors.shape[1] > 1 else 0
        order = np.argsort(eigenvectors[:, fiedler_index])
        labels = np.empty(eigenvectors.shape[0], dtype=np.int64)
        for group, members in enumerate(np.array_split(order, k)):
            labels[members] = group
        return labels

    @staticmethod
    def _labels_to_kpartition(
        nodes: tuple[int, ...],
        labels: NDArray[np.int64],
        future_universe: tuple[int, ...],
        present_universe: tuple[int, ...],
    ) -> KPartition:
        """Build a node-aligned ``KPartition`` from cluster labels.

        Each node's future and present atom go to the block of its label;
        present indices not present as nodes default to the first block.
        """
        node_label = {node: int(label) for node, label in zip(nodes, labels, strict=True)}
        k = len(set(node_label.values()))
        future_blocks: list[list[int]] = [[] for _ in range(k)]
        present_blocks: list[list[int]] = [[] for _ in range(k)]

        # Re-map labels to a contiguous 0..k-1 range to index the block lists.
        label_order = {label: position for position, label in enumerate(sorted(set(node_label.values())))}

        for future_index in future_universe:
            future_blocks[label_order[node_label[future_index]]].append(future_index)
        for present_index in present_universe:
            label = node_label.get(present_index, sorted(node_label.values())[0])
            present_blocks[label_order[label]].append(present_index)

        return KPartition.from_blocks(
            blocks=[
                (tuple(sorted(future_blocks[r])), tuple(sorted(present_blocks[r])))
                for r in range(k)
            ],
            future_universe=future_universe,
            present_universe=present_universe,
        )
