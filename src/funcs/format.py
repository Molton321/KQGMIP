from src.constants.base import COLON_DELIM, EMPTY_STR, VOID_STR, WIDTH_PADDING
from src.funcs.labels import ABECEDARY, LOWER_ABECEDARY


def fmt_kpartition(
    signature: tuple[tuple[tuple[int, ...], tuple[int, ...]], ...],
) -> str:
    """Render a k-partition in human-readable block format.

    ``signature`` is a sequence of ``(purview_block, mechanism_block)`` pairs
    (as produced by ``KPartition.signature``). Each block is shown on its own
    line as ``Bi: <mechanism> | <purview>``, using upper-case letters for
    purview (future) indices and lower-case for mechanism (present) indices;
    an empty side is rendered as ``∅``.
    """
    lines: list[str] = []
    for idx, (purview_block, mechanism_block) in enumerate(signature, start=1):
        purview_text = (
            VOID_STR if not purview_block else EMPTY_STR.join(ABECEDARY[i] for i in purview_block)
        )
        mechanism_text = (
            VOID_STR
            if not mechanism_block
            else EMPTY_STR.join(LOWER_ABECEDARY[i] for i in mechanism_block)
        )
        lines.append(f"B{idx}: {mechanism_text} | {purview_text}")
    return "\n".join(lines)


def fmt_bipartition(
    part_one: list,
    part_two: list,
) -> str:
    """
    Format a bipartition using mathematical bracket notation.

    Each part is [mechanism_indices, purview_indices]. Inputs may be
    numpy arrays, tuples or sets; the emptiness check uses `len()` to
    work uniformly across all of them.
    """
    mech_p, pur_p = part_one
    mech_d, purv_d = part_two

    purv_prim = COLON_DELIM.join(ABECEDARY[j] for j in pur_p) if len(pur_p) else VOID_STR
    mech_prim = COLON_DELIM.join(LOWER_ABECEDARY[i] for i in mech_p) if len(mech_p) else VOID_STR
    purv_dual = COLON_DELIM.join(ABECEDARY[i] for i in purv_d) if len(purv_d) else VOID_STR
    mech_dual = COLON_DELIM.join(LOWER_ABECEDARY[j] for j in mech_d) if len(mech_d) else VOID_STR

    width_prim = max(len(purv_prim), len(mech_prim)) + WIDTH_PADDING
    width_dual = max(len(purv_dual), len(mech_dual)) + WIDTH_PADDING

    return (
        f"⎛{purv_prim:^{width_prim}}⎞⎛{purv_dual:^{width_dual}}⎞\n"
        f"⎝{mech_prim:^{width_prim}}⎠⎝{mech_dual:^{width_dual}}⎠\n"
    )


def fmt_bipartition_q(
    prim: list[tuple[int, int]],
    dual: list[tuple[int, int]],
    to_sort: bool = True,
) -> str:
    """Format a bipartition in Q-Nodes form (list of (time, index) tuples)."""
    top_prim, bottom_prim = fmt_part_q(prim, to_sort)
    top_dual, bottom_dual = fmt_part_q(dual, to_sort)
    return f"{top_prim}{top_dual}\n{bottom_prim}{bottom_dual}\n"


def fmt_part_q(
    part: list[tuple[int, int]], to_sort: bool = True
) -> tuple[str, str]:
    if to_sort:
        part.sort(key=lambda x: x[1])

    purv, mech = [], []
    for time, idx in part:
        purv.append(ABECEDARY[idx]) if time else mech.append(LOWER_ABECEDARY[idx])

    str_purv = COLON_DELIM.join(purv) if purv else VOID_STR
    str_mech = COLON_DELIM.join(mech) if mech else VOID_STR
    width = max(len(str_purv), len(str_mech)) + 2

    return f"⎛{str_purv:^{width}}⎞", f"⎝{str_mech:^{width}}⎠"
