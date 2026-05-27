import time
from typing import Callable

import numpy as np
import pandas as pd
from colorama import Fore
from numpy.typing import NDArray

from src.base.application import aplicacion
from src.base.sia import SIA
from src.constants.base import ACTUAL, COLS_IDX, EFECTO, EXCEL_EXTENSION, FLOAT_ZERO, NET_LABEL, TYPE_TAG
from src.constants.tags import (
    BRUTEFORCE_ANALYSIS_TAG,
    BRUTEFORCE_FULL_ANALYSIS_TAG,
    BRUTEFORCE_LABEL,
    BRUTEFORCE_STRATEGY_TAG,
    DUMMY_ARR,
    DUMMY_EMD,
    ERROR_PARTITION,
)
from src.funcs.emd import seleccionar_emd
from src.funcs.format import fmt_biparticion
from src.funcs.labels import literales
from src.funcs.partitions import biparticiones, generar_candidatos, generar_particiones, generar_subsistemas
from src.io.logger import SafeLogger
from src.io.profiler import gestor_perfilado, profile
from src.models.solution import Solution
from src.models.system import System


class BruteForce(SIA):
    """
    Estrategia de fuerza bruta: evalúa todas las biparticiones posibles y
    selecciona la que minimiza la EMD respecto al subsistema original.

    Complejidad: O(2^(m+n)) donde m = |alcance|, n = |mecanismo|.
    """

    def __init__(self, tpm: np.ndarray, estado_inicial: str):
        super().__init__(tpm, estado_inicial)
        gestor_perfilado.start_session(
            f"{NET_LABEL}{len(tpm[COLS_IDX])}{aplicacion.pagina_red_muestra}"
        )
        self.distancia_metrica: Callable = seleccionar_emd()
        self.logeador = SafeLogger(BRUTEFORCE_STRATEGY_TAG)

    def aplicar_estrategia(
        self, condicion: str, alcance: str, mecanismo: str
    ) -> "Solution":
        self.sia_preparar_subsistema(condicion, alcance, mecanismo)

        solucion = Solution(
            BRUTEFORCE_LABEL,
            DUMMY_EMD,
            self.sia_dists_marginales,
            DUMMY_ARR,
            ERROR_PARTITION,
        )

        small_phi = np.inf
        mejor_dist: np.ndarray = DUMMY_ARR

        futuros = self.sia_subsistema.indices_ncubos
        presentes = self.sia_subsistema.dims_ncubos
        m, n = futuros.size, presentes.size

        for subalcance, submecanismo in biparticiones(futuros, presentes, (1 << m) * (1 << n)):
            arr_alcance = np.array(subalcance, dtype=np.int8)
            arr_mecanismo = np.array(submecanismo, dtype=np.int8)

            particion = self.sia_subsistema.bipartir(arr_alcance, arr_mecanismo)
            dist_part = particion.distribucion_marginal()
            emd_val = self.distancia_metrica(dist_part, self.sia_dists_marginales)

            if emd_val < small_phi:
                small_phi = emd_val
                mejor_dist = dist_part
                bipart_prim = submecanismo, subalcance
                bipart_dual = (
                    set(presentes.data) - set(submecanismo),
                    set(futuros.data) - set(subalcance),
                )
                if emd_val == FLOAT_ZERO:
                    solucion.perdida = emd_val
                    solucion.distribucion_particion = dist_part
                    solucion.particion = fmt_biparticion(
                        [bipart_prim[ACTUAL], bipart_prim[EFECTO]],
                        [bipart_dual[ACTUAL], bipart_dual[EFECTO]],
                    )
                    solucion.tiempo_ejecucion = time.time() - self.sia_tiempo_inicio
                    return solucion

        solucion.perdida = small_phi
        solucion.distribucion_particion = mejor_dist
        solucion.particion = fmt_biparticion(
            [bipart_prim[ACTUAL], bipart_prim[EFECTO]],
            [bipart_dual[ACTUAL], bipart_dual[EFECTO]],
        )
        solucion.tiempo_ejecucion = time.time() - self.sia_tiempo_inicio
        return solucion

    @profile(context={TYPE_TAG: BRUTEFORCE_FULL_ANALYSIS_TAG})
    def analizar_red_completa(self, output_dir) -> None:
        """
        Análisis exhaustivo de una red: genera todos los sistemas candidatos,
        subsistemas y biparticiones, guardando resultados en Excel.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        dims_estado = np.array([int(b) for b in self.estado_inicial], dtype=np.int8)
        sistema = System(self.tpm, dims_estado)
        cantidad = len(self.estado_inicial)

        for dims in generar_candidatos(cantidad):
            candidato = sistema.condicionar(np.array(dims, dtype=np.int8))
            nombre = literales(np.setdiff1d(candidato.dims_ncubos, np.array(dims, dtype=np.int8)))
            results_file = output_dir / f"{nombre}.{EXCEL_EXTENSION}"

            with pd.ExcelWriter(results_file) as writer:
                for alc_rem, mec_rem in generar_subsistemas(candidato.dims_ncubos):
                    if len(alc_rem) == candidato.indices_ncubos.size:
                        continue
                    subsistema = candidato.substraer(
                        np.array(alc_rem, dtype=np.int8),
                        np.array(mec_rem, dtype=np.int8),
                    )
                    dist = subsistema.distribucion_marginal()
                    m = subsistema.indices_ncubos.size
                    n = subsistema.dims_ncubos.size

                    resultados = pd.DataFrame(
                        columns=[f"{i:0{m}b}" for i in range(1 << (m - 1))],
                        index=[f"{i:0{n}b}" for i in range(1 << n)],
                        dtype=np.float32,
                    )
                    for alc_bits, mec_bits in generar_particiones(m, n):
                        sub_alc = np.array([i for i, b in enumerate(alc_bits) if b], dtype=np.int8)
                        sub_mec = np.array([i for i, b in enumerate(mec_bits) if b], dtype=np.int8)
                        part = subsistema.bipartir(sub_alc, sub_mec)
                        emd_val = self.distancia_metrica(part.distribucion_marginal(), dist)
                        resultados.loc[
                            "".join(map(str, mec_bits.astype(int))),
                            "".join(map(str, alc_bits.astype(int))),
                        ] = emd_val

                    fut_rem = np.setdiff1d(candidato.dims_ncubos, np.array(alc_rem, dtype=np.int8))
                    pres_rem = np.setdiff1d(candidato.dims_ncubos, np.array(mec_rem, dtype=np.int8))
                    sheet = f"{literales(fut_rem)}|{literales(pres_rem)}"
                    resultados.to_excel(writer, sheet_name=sheet)

        print(f"{Fore.GREEN}Análisis completo. Revisa review/resolver/")
