import contextlib
import io

from src.controllers.manager import Manager
from src.models.base.application import application


def run_strategy(net, strategy_cls):
    n = int(net[1:-1])
    page = net[-1]
    state = "1" * n
    application.set_sample_network_page(page)
    tpm = Manager(state).load_network()
    full = "1" * n
    with contextlib.redirect_stdout(io.StringIO()):
        solution = strategy_cls(tpm, state).apply_strategy(full, full, full)
    return solution
