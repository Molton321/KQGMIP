"""
Clustering-based SIA strategy that proposes a k-partition by clustering the node affinity graph.
"""

import time

import numpy as np
from numpy.typing import NDArray
from scipy.cluster.vq import ClusterError, kmeans2
from scipy.sparse.csgraph import laplacian

from src.constants.base import COLS_IDX, NET_LABEL, TYPE_TAG
from src.constants.strategies import (
    CLUSTERING_ANALYSIS_TAG,
    CLUSTERING_LABEL,
    CLUSTERING_STRATEGY_TAG,
    MAX_AFFINITY_SAMPLE,
)
from src.funcs.emd import delta_k
from src.funcs.format import fmt_kpartition
from src.middlewares.profile import profile, profiling_manager
from src.middlewares.slogger import SafeLogger
from src.models.base.application import application
from src.models.base.sia import SIA
from src.models.core.partition import KPartition
from src.models.core.solution import Solution


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
        loss, distribution = delta_k(
            subsystem, partition, baseline_distribution=baseline
        )
        self.best_partition = partition

        return Solution(
            strategy=f"{CLUSTERING_LABEL}({self.method}, k={self.k})",
            loss=float(loss),
            subsystem_distribution=baseline,
            partition_distribution=distribution,
            total_time=time.perf_counter() - self.sia_start_time,
            partition=fmt_kpartition(partition.signature),
        )

    def _node_features(self, nodes: tuple[int, ...]) -> NDArray[np.float64]:
        """
        Binarized behaviour of each node over a deterministic TPM-row sample.
        Returns an (n, sample) matrix where row i is the 0/1 response of
        node nodes[i] across the sampled states. Two nodes that respond
        alike across states are considered similar.
        """
        n_rows = self.tpm.shape[0]
        rng = np.random.default_rng(application.numpy_seed)
        if n_rows > MAX_AFFINITY_SAMPLE:
            sample = rng.choice(n_rows, MAX_AFFINITY_SAMPLE, replace=False)
        else:
            sample = np.arange(n_rows)

        columns = self.tpm[np.ix_(sample, np.asarray(nodes, dtype=np.intp))]
        return (columns > 0.5).astype(np.float64).T

    def _affinity(self, features: NDArray[np.float64]) -> NDArray[np.float64]:
        """Agreement-fraction affinity matrix W[i,j] ∈ [0, 1] between nodes."""
        sample_size = features.shape[1]
        agreement = (features @ features.T) + ((1 - features) @ (1 - features).T)
        weights = agreement / max(sample_size, 1)
        np.fill_diagonal(weights, 0.0)
        return weights

    def _cluster(self, features: NDArray[np.float64], k: int) -> NDArray[np.int64]:
        """
        Cluster nodes into k groups using spectral clustering.
        """

        weights = self._affinity(features)
        normalized_laplacian = laplacian(weights, normed=True)
        _, eigenvectors = np.linalg.eigh(normalized_laplacian)

        if self.method == "kmeans":
            data = features
        else:
            embedding = eigenvectors[:, :k]
            norms = np.linalg.norm(embedding, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            data = embedding / norms

        labels = None

        try:
            with np.errstate(invalid="ignore", divide="ignore"):
                _, labels = kmeans2(
                    data, k, rng=application.numpy_seed, minit="++", missing="raise"
                )
        except (ValueError, ClusterError) as e:
            self.logger.warn(
                f"k-means failed with error: {e}. Falling back to Fiedler split."
            )

        if labels is None or len(set(int(x) for x in labels)) < k:
            labels = self._fiedler_split(eigenvectors, k)
        return np.asarray(labels, dtype=np.int64)

    @staticmethod
    def _fiedler_split(eigenvectors: NDArray[np.float64], k: int) -> NDArray[np.int64]:
        """
        Fallback method to split nodes into k groups based on the Fiedler vector
        (the eigenvector corresponding to the second smallest eigenvalue of the Laplacian).
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
        """
        Convert node labels to a KPartition by grouping future and present indices
        according to the node labels. Each block r in the partition corresponds to
        the set of future indices whose nodes have label r, and the set of present indices
        whose nodes have label r (or a default label if not present in node_label).
        """
        node_label = {
            node: int(label) for node, label in zip(nodes, labels, strict=True)
        }
        k = len(set(node_label.values()))
        future_blocks: list[list[int]] = [[] for _ in range(k)]
        present_blocks: list[list[int]] = [[] for _ in range(k)]

        label_order = {
            label: position
            for position, label in enumerate(sorted(set(node_label.values())))
        }

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
