import numpy as np
import pytest

from src.controllers.manager import Manager
from src.funcs.emd import delta_k, effect_emd
from src.funcs.partitions import bipartitions
from src.models.base.application import application
from src.models.core.partition import KPartition
from src.models.core.system import System


@pytest.mark.parametrize("net", ["N2A", "N3A", "N4A"])
def test_delta_k_matches_legacy_bipartition_for_k2(net: str) -> None:
    n = int(net[1:-1])
    page = net[-1]
    state = "1" * n

    application.set_sample_network_page(page)
    tpm = Manager(state).load_network()

    system = System(tpm, np.array([int(bit) for bit in state], dtype=np.int8))
    baseline = system.marginal_distribution()

    effects = system.ncube_indices
    causes = system.ncube_dims

    for idx, (purview_sel, mechanism_sel) in enumerate(
        bipartitions(effects, causes, (1 << effects.size) * (1 << causes.size))
    ):
        if idx >= 10:
            break

        purview_arr = np.array(purview_sel, dtype=np.int8)
        mechanism_arr = np.array(mechanism_sel, dtype=np.int8)

        legacy_dist = system.bipartition(purview_arr, mechanism_arr).marginal_distribution()
        legacy_loss = effect_emd(legacy_dist, baseline)

        kpartition = KPartition.from_blocks(
            blocks=[
                (purview_arr, mechanism_arr),
                (np.setdiff1d(effects, purview_arr), np.setdiff1d(causes, mechanism_arr)),
            ],
            future_universe=effects,
            present_universe=causes,
        )
        k_loss, k_dist = delta_k(system, kpartition, baseline_distribution=baseline)

        assert k_loss == pytest.approx(legacy_loss, abs=1e-9)
        assert np.allclose(k_dist, legacy_dist, atol=1e-9)
