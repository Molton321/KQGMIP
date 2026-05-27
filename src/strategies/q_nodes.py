import time
from typing import Union

import numpy as np

from src.base.application import aplicacion
from src.base.sia import SIA
from src.constants.base import ACTUAL, COLS_IDX, EFECTO, INFTY_POS, INT_ZERO, LAST_IDX, NET_LABEL, TYPE_TAG
from src.constants.tags import QNODES_ANALYSIS_TAG, QNODES_LABEL, QNODES_STRATEGY_TAG
from src.funcs.emd import emd_efecto
from src.funcs.format import fmt_biparticion_q
from src.funcs.labels import ABECEDARY
from src.io.logger import SafeLogger
from src.io.profiler import gestor_perfilado, profile
from src.models.solution import Solution


class QNodes(SIA):
    """
    Estrategia Q-Nodes: algoritmo greedy submodular para buscar la MIP.

    Construye incrementalmente conjuntos de nodos que minimizan la pérdida
    de información. Complejidad polinomial frente a la fuerza bruta exponencial.
    """

    def __init__(self, tpm: np.ndarray, estado_inicial: str):
        super().__init__(tpm, estado_inicial)
        gestor_perfilado.start_session(
            f"{NET_LABEL}{len(tpm[COLS_IDX])}{aplicacion.pagina_red_muestra}"
        )
        self.etiquetas = [tuple(s.lower() for s in ABECEDARY), ABECEDARY]
        self.vertices: set[tuple]
        self.clave_submodular = [], []
        self.memoria_delta: dict = {}
        self.memoria_grupo_candidato: dict = {}
        self.indices_alcance: np.ndarray
        self.indices_mecanismo: np.ndarray
        self.logger = SafeLogger(QNODES_STRATEGY_TAG)

    def aplicar_estrategia(
        self, condicion: str, alcance: str, mecanismo: str
    ) -> Solution:
        self.sia_preparar_subsistema(condicion, alcance, mecanismo)

        futuro = tuple(
            (EFECTO, idx) for idx in self.sia_subsistema.indices_ncubos
        )
        presente = tuple(
            (ACTUAL, idx) for idx in self.sia_subsistema.dims_ncubos
        )

        self.indices_alcance = self.sia_subsistema.indices_ncubos
        self.indices_mecanismo = self.sia_subsistema.dims_ncubos

        vertices = list(presente + futuro)
        self.vertices = set(presente + futuro)
        mip = self.algorithm(vertices)

        fmt_mip = fmt_biparticion_q(list(mip), self.nodes_complement(mip))
        perdida_mip, dist_mip = self.memoria_grupo_candidato[mip]

        return Solution(
            estrategia=QNODES_LABEL,
            perdida=perdida_mip,
            distribucion_subsistema=self.sia_dists_marginales,
            distribucion_particion=dist_mip,
            tiempo_total=time.time() - self.sia_tiempo_inicio,
            particion=fmt_mip,
        )

    @profile(context={TYPE_TAG: QNODES_ANALYSIS_TAG})
    def algorithm(self, vertices: list[tuple[int, int]]) -> tuple:
        """
        Algoritmo Q para encontrar la bipartición de menor pérdida.

        Opera en fases (i) > ciclos (j) > iteraciones (k):
        - Omega crece incorporando el delta de menor ganancia submodular.
        - Al final de cada fase se forma un par candidato.
        - Se retorna la partición con menor EMD global.
        """
        indice_emd = INT_ZERO

        for i in range(len(vertices) - 1):
            omegas = [vertices[0]]
            deltas = vertices[1:]
            emd_candidata = INFTY_POS
            dist_candidata = None

            for j in range(len(deltas) - 1):
                emd_local = 1e5
                indice_mip: int

                for k in range(len(deltas)):
                    emd_union, emd_delta, dist_delta = self.funcion_submodular(
                        deltas[k], omegas
                    )
                    ganancia = emd_union - emd_delta

                    if ganancia < emd_local:
                        if emd_delta == INT_ZERO:
                            clave = (
                                tuple(deltas[k])
                                if isinstance(deltas[k], list)
                                else (deltas[k],)
                            )
                            self.memoria_grupo_candidato[clave] = (emd_delta, dist_delta)
                            return clave

                        emd_local = ganancia
                        indice_mip = k
                        emd_candidata = emd_delta
                        dist_candidata = dist_delta

                omegas.append(deltas[indice_mip])
                deltas.pop(indice_mip)

            self.memoria_grupo_candidato[
                tuple(
                    deltas[LAST_IDX]
                    if isinstance(deltas[LAST_IDX], list)
                    else deltas
                )
            ] = emd_candidata, dist_candidata

            par_candidato = (
                [omegas[LAST_IDX]] if isinstance(omegas[LAST_IDX], tuple) else omegas[LAST_IDX]
            ) + (
                deltas[LAST_IDX] if isinstance(deltas[LAST_IDX], list) else deltas
            )

            omegas.pop()
            omegas.append(par_candidato)
            vertices = omegas

        return min(
            self.memoria_grupo_candidato,
            key=lambda k: self.memoria_grupo_candidato[k][indice_emd],
        )

    def funcion_submodular(
        self,
        deltas: Union[tuple, list[tuple]],
        omegas: list,
    ) -> tuple[float, float, np.ndarray]:
        """
        Evalúa la ganancia marginal de añadir `deltas` al conjunto `omegas`.

        Retorna: (emd_union, emd_delta, dist_marginal_delta)
        """
        self.clave_submodular = [], []

        clave_actual, clave_efecto = self.definir_clave(deltas)
        clave_delta = tuple(clave_actual), tuple(clave_efecto)

        idxs_alc = self.clave_submodular[EFECTO]
        dims_mec = self.clave_submodular[ACTUAL]

        if clave_delta not in self.memoria_delta:
            part_delta = self.sia_subsistema.bipartir(
                np.array(idxs_alc, dtype=np.int8),
                np.array(dims_mec, dtype=np.int8),
            )
            dist_delta = part_delta.distribucion_marginal()
            emd_delta = emd_efecto(dist_delta, self.sia_dists_marginales)
            self.memoria_delta[clave_delta] = emd_delta, dist_delta
        else:
            emd_delta, dist_delta = self.memoria_delta[clave_delta]

        for omega in omegas:
            self.definir_clave(omega)

        part_union = self.sia_subsistema.bipartir(
            np.array(self.clave_submodular[EFECTO], dtype=np.int8),
            np.array(self.clave_submodular[ACTUAL], dtype=np.int8),
        )
        dist_union = part_union.distribucion_marginal()
        emd_union = emd_efecto(dist_union, self.sia_dists_marginales)

        return emd_union, emd_delta, dist_delta

    def definir_clave(self, conjunto: Union[tuple, list[tuple]]):
        if isinstance(conjunto, tuple):
            tiempo, indice = conjunto
            self.clave_submodular[tiempo].append(indice)
        else:
            for tiempo, indice in conjunto:
                self.clave_submodular[tiempo].append(indice)
        self.clave_submodular[ACTUAL].sort()
        self.clave_submodular[EFECTO].sort()
        return self.clave_submodular

    def nodes_complement(self, nodes) -> list:
        return list(set(self.vertices) - set(nodes))
