"""
Phi strategy implementation using the PyPhi library.
"""

import math
import time

import numpy as np
from pyphi import Network, Subsystem
from pyphi.labels import NodeLabels

from src.constants.base import COLS_IDX, NET_LABEL, STR_ONE, TYPE_TAG
from src.constants.strategies import PYPHI_ANALYSIS_TAG, PYPHI_LABEL, PYPHI_STRATEGY_TAG
from src.constants.tags import DUMMY_ARR, DUMMY_PARTITION
from src.funcs.format import fmt_bipartition
from src.funcs.labels import ABECEDARY, lil_endian
from src.middlewares.profile import profile, profiling_manager
from src.middlewares.slogger import SafeLogger
from src.models.base.application import application
from src.models.base.sia import SIA
from src.models.core.solution import Solution
from src.models.enums.temporal_emd import TimeEMD


class Phi(SIA):
    """
    PyPhi strategy: wraps the reference pyphi library to compute the MIP
    using its standard implementation.
    Useful for validating the results of the other strategies.
    """

    def __init__(self, tpm: np.ndarray, initial_state: str) -> None:
        super().__init__(tpm, initial_state)
        profiling_manager.start_session(
            f"{NET_LABEL}{len(tpm[COLS_IDX])}{application.sample_network_page}"
        )
        self.logger = SafeLogger(PYPHI_STRATEGY_TAG)

    @profile(context={TYPE_TAG: PYPHI_ANALYSIS_TAG})
    def apply_strategy(self, condition: str, purview: str, mechanism: str) -> Solution:
        self.sia_start_time = time.time()
        length = len(self.initial_state)
        state = tuple(int(s) for s in self.initial_state)
        indices = tuple(range(length))
        label_names = tuple(ABECEDARY[:length])
        labels = NodeLabels(label_names, indices)

        network = Network(tpm=self.tpm, node_labels=labels)
        candidate = tuple(labels[i] for i, b in enumerate(condition) if b == STR_ONE)
        subsystem = Subsystem(network=network, state=state, nodes=candidate)
        self.logger.critic("Subsistema creado.")

        purview_idxs = tuple(
            i
            for i, (b, c) in enumerate(zip(purview, condition, strict=False))
            if b == STR_ONE and c == STR_ONE
        )
        mechanism_idxs = tuple(
            i
            for i, (b, c) in enumerate(zip(mechanism, condition, strict=False))
            if b == STR_ONE and c == STR_ONE
        )

        emd_time = application.emd_time
        if isinstance(emd_time, TimeEMD):
            emd_time = emd_time.value

        mip = (
            subsystem.effect_mip(mechanism_idxs, purview_idxs)
            if emd_time == TimeEMD.EMD_EFFECT.value
            else subsystem.cause_mip(mechanism_idxs, purview_idxs)
        )

        small_phi = mip.phi
        repertoire = partitioned_repertoire = DUMMY_ARR
        fmt = DUMMY_PARTITION

        if mip.repertoire is not None:
            repertoire = mip.repertoire.flatten()
            partitioned_repertoire = mip.partitioned_repertoire.flatten()

            states = int(math.log2(mip.repertoire.size))
            sub_states = lil_endian(states)
            repertoire.put(sub_states, repertoire)
            partitioned_repertoire.put(sub_states, partitioned_repertoire)

            best = mip.partition
            prim = best.parts[True]
            dual = best.parts[False]
            fmt = fmt_bipartition(
                [dual.mechanism, dual.purview],
                [prim.mechanism, prim.purview],
            )

        return Solution(
            strategy=PYPHI_LABEL,
            loss=small_phi,
            subsystem_distribution=repertoire,
            partition_distribution=partitioned_repertoire,
            total_time=time.perf_counter() - self.sia_start_time,
            partition=fmt,
        )
