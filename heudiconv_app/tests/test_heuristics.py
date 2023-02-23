# run via entering into this folder (heudiconv_app/tests)
# then pytest test_heuristics.py

import re
import sys

sys.path.append("../assets")

from a2cps import protocols2fix

p2f: dict[str, list[tuple[str, str]]] = protocols2fix

anatomical = {"anat-T1w": ["T1_MPRAGE", "T1_MPRAGE_R1", "T1_MPRAGE R1"]}
dwi = {"dwi": ["DWI", "dwi"]}
rest = {"func_task-rest_run-1": ["Rest1", "REST1"]}
cuff = {"func_task-cuff_run-1": ["Cuff1", "CUFF1"]}
dwib0 = {"fmap-epi_acq-dwib0": ["DWI_B0"]}
fmrib0 = {"fmap-epi_acq-fmrib0": ["fMRI_B0"]}


SCANS = [anatomical, dwi, rest, cuff, dwib0, fmrib0]


def test_substitutions():
    for scan in SCANS:
        for expected, observed in scan.items():
            results = set()
            for i in observed:
                value = i
                for _, substitutions in p2f.items():
                    for substring, replacement in substitutions:
                        value = re.sub(substring, replacement, value)
                results.update([value])
                print(f"{i} -> {value}")

            assert results == set([expected])
