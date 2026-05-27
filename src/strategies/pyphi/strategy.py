import math
import time

import numpy as np

from src.base.application import aplicacion
from src.base.sia import SIA
from src.constants.base import COLS_IDX, NET_LABEL, STR_ONE, TYPE_TAG
from src.constants.tags import DUMMY_ARR, DUMMY_PARTITION
from src.strategies.pyphi.tags import PYPHI_ANALYSIS_TAG, PYPHI_LABEL, PYPHI_STRATEGY_TAG
from src.funcs.format import fmt_biparticion
from src.funcs.labels import ABECEDARY, lil_endian
from src.io.logger import SafeLogger
from src.io.profiler import gestor_perfilado, profile
from src.models.enums.temporal_emd import TimeEMD
from src.models.solution import Solution


class Phi(SIA):
    """
    Estrategia PyPhi: envuelve la librería de referencia pyphi para
    calcular la MIP usando su implementación estándar.

    Útil para validar resultados de otras estrategias.
    """

    def __init__(self, tpm: np.ndarray, estado_inicial: str) -> None:
        super().__init__(tpm, estado_inicial)
        gestor_perfilado.start_session(
            f"{NET_LABEL}{len(tpm[COLS_IDX])}{aplicacion.pagina_red_muestra}"
        )
        self.logger = SafeLogger(PYPHI_STRATEGY_TAG)

    @profile(context={TYPE_TAG: PYPHI_ANALYSIS_TAG})
    def aplicar_estrategia(
        self, condicion: str, alcance: str, mecanismo: str
    ) -> Solution:
        try:
            from pyphi import Network, Subsystem
            from pyphi.labels import NodeLabels
        except ImportError:
            raise ImportError("pyphi no está instalado. Instálalo con: pip install pyphi")

        self.sia_tiempo_inicio = time.time()
        longitud = len(self.estado_inicial)
        estado = tuple(int(s) for s in self.estado_inicial)
        indices = tuple(range(longitud))
        etiquetas = tuple(ABECEDARY[:longitud])
        labels = NodeLabels(etiquetas, indices)

        red = Network(tpm=self.tpm, node_labels=labels)
        candidato = tuple(labels[i] for i, b in enumerate(condicion) if b == STR_ONE)
        subsistema = Subsystem(network=red, state=estado, nodes=candidato)
        self.logger.critic("Subsistema creado.")

        purview = tuple(
            i for i, (b, c) in enumerate(zip(alcance, condicion))
            if b == STR_ONE and c == STR_ONE
        )
        mechanism = tuple(
            i for i, (b, c) in enumerate(zip(mecanismo, condicion))
            if b == STR_ONE and c == STR_ONE
        )

        tiempo_emd = aplicacion.tiempo_emd
        if isinstance(tiempo_emd, TimeEMD):
            tiempo_emd = tiempo_emd.value

        mip = (
            subsistema.effect_mip(mechanism, purview)
            if tiempo_emd == TimeEMD.EMD_EFECTO.value
            else subsistema.cause_mip(mechanism, purview)
        )

        small_phi = mip.phi
        repertorio = repertorio_partido = DUMMY_ARR
        fmt = DUMMY_PARTITION

        if mip.repertoire is not None:
            repertorio = mip.repertoire.flatten()
            repertorio_partido = mip.partitioned_repertoire.flatten()

            states = int(math.log2(mip.repertoire.size))
            sub_estados = lil_endian(states)
            repertorio.put(sub_estados, repertorio)
            repertorio_partido.put(sub_estados, repertorio_partido)

            mejor = mip.partition
            prim = mejor.parts[True]
            dual = mejor.parts[False]
            fmt = fmt_biparticion(
                [dual.mechanism, dual.purview],
                [prim.mechanism, prim.purview],
            )

        return Solution(
            estrategia=PYPHI_LABEL,
            perdida=small_phi,
            distribucion_subsistema=repertorio,
            distribucion_particion=repertorio_partido,
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            particion=fmt,
        )
