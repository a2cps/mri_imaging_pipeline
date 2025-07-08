# run via entering into this folder (heudiconv_app/tests)
# then pytest test_heuristics.py

import re
import sys

sys.path.append("../assets")

from a2cps import protocols2fix

p2f: dict[str, list[tuple[str, str]]] = protocols2fix

anatomical = {
    "anat-T1w": [
        "T1_MPRAGE",
        "T1_MPRAGE_R1",
        "T1_MPRAGE R1",
        "Tra T1 MPRAGE orthog",
        "anat-T1w_acq-MPRAGE",
        "Sag T1_MPRAGE",
    ]
}
dwi = {"dwi": ["DWI", "dwi", "DTI", "ORIG: DTI", "dMRI"]}
rest = {
    "func_task-rest_run-1": [
        "Rest1",
        "REST1",
        "DelRec - REST1",
        "WIP DelRec - REST1",
    ]
}
cuff = {"func_task-cuff_run-1": ["Cuff1", "CUFF1", "CUFF1R2", "CUFF1R2"]}
dwib0 = {"fmap-epi_acq-dwib0": ["DWI_B0"]}
fmrib0 = {"fmap-epi_acq-fmrib0": ["fMRI_B0"]}
dwib1000 = {"dwi-dwi_acq-b1000": ["DWI_b1000_17DSV", "DWI_B1000_17DSV"]}
dwib2000 = {"dwi-dwi_acq-b2000": ["DWI_b2000_17DSV", "DWI_B2000_17DSV"]}


SCANS = [anatomical, dwi, rest, cuff, dwib0, fmrib0, dwib1000, dwib2000]


def _apply_substitutions(
    mappings: dict[str, list[tuple[str, str]]], original: str
) -> str:
    # cf https://github.com/nipy/heudiconv/blob/94911c7d1605c076f6f62c3943dc8a5ad74ba8c6/heudiconv/heuristics/reproin.py#L334
    out = original
    for _, substitutions in mappings.items():
        for substring, replacement in substitutions:
            out = re.sub(substring, replacement, out)
    return out


def test_substitutions():
    for scan in SCANS:
        for expected, observed in scan.items():
            for i in observed:
                print(i)
                value = _apply_substitutions(p2f, i)
                if not value == expected:
                    msg = f"Failed to produce expected protocol {value=} {expected=}"
                    raise RuntimeError(msg)
