import argparse
import json
import logging
import os
import pathlib
import re
import typing
from glob import glob
from itertools import chain

import ancpbids
import numpy as np
import pandas as pd
from deepdiff import DeepDiff
from utils import print_and_post

# parameters to check for numerical equivalence
FLOATING_PARAMS = {
    0.001: [
        "dcmmeta_affine",
        "EffectiveEchoSpacing",
        "RepetitionTime",
        "ImageOrientationPatientDICOM",
    ],
    0.01: ["ImagingFrequency", "WaterFatShift"],
    0.1: ["SliceTiming", "EchoTime"],
}

SIEMENS_W_64 = ["NS", "SH", "RU"]

def add_deepkeys(observed: dict[str, typing.Any]) -> dict[str, typing.Any]:
    if observed.__contains__("global"):
        observed["BitsStored"] = observed.get("global").get("const").get("BitsStored")  # type: ignore
    return observed


def tidy_metadata(meta: dict[str, typing.Any]):
    del meta["global"]
    return meta

def get_metadata(file: str) -> dict[str, typing.Any]:
    """get_metadata associated with nii.gz file

    Args:
        file (str): nifti file

    Returns:
        dict[str, typing.Any]: contents of associated json sidecar

    Description:
        Unlike layout.get_metadata(), this function does not collapse
        keys that appear in multiple positions
    """
    if not file.endswith("nii.gz"):
        msg = f"expecting file that ends with nii.gz, received {file}"
        raise AssertionError(msg)
    
    meta = json.loads(pathlib.Path(file.replace("nii.gz", "json")).read_text())
    meta = add_deepkeys(meta)
    meta = tidy_metadata(meta)

    return meta


def remove_translation(meta: dict) -> dict:
    if (affine := meta.get("dcmmeta_affine")) is not None:
        for i, row in enumerate(affine):
            meta["dcmmeta_affine"][i] = row[0:-1]

    return meta


def assert_constant(
    jsons: list, meta: list, key: str, post: bool = False
) -> bool:
    tocheck = pd.DataFrame(
        {
            "json": [os.path.basename(x) for x in jsons],
            key: [x.get(key) for x in meta],
        }
    )

    if len(tocheck.drop_duplicates(subset=key)) > 1:
        print_and_post(
            f"Visit has multiple values for {key}\n" + tocheck.to_string(),
            post=post,
        )
        ok = False
    else:
        ok = True

    return ok


def compare_withinsub(
    layout: ancpbids.BIDSLayout, site: str, post: bool = False
) -> bool:
    """
    Some parameters won't be consistant from participant to participant, even while
    they should have a single value within a session. This function organizes checks for
    that consistency

    """
    json_list: list[str] = (
        layout.get(suffix="T1w", extension="nii.gz", return_type="file")
        + layout.get(task="cuff", extension="nii.gz", return_type="file")
        + layout.get(task="rest", extension="nii.gz", return_type="file")
        + layout.get(suffix="dwi", extension="nii.gz", return_type="file")
        + layout.get(suffix="epi", extension="nii.gz", return_type="file")
    )  # type: ignore
    meta_list = [get_metadata(x) for x in json_list]

    if site in SIEMENS_W_64:
        ok = assert_constant(
            json_list, meta_list, "ReceiveCoilActiveElements", post=post
        )
    elif site == "WS":
        ok = assert_constant(json_list, meta_list, "CoilString", post=post)
    else:
        ok = True

    func_list: list[str] = (
        layout.get(task="rest", extension="nii.gz", return_type="file")
        + layout.get(task="cuff", extension="nii.gz", return_type="file")
        + layout.get(
            suffix="epi", extension="nii.gz", return_type="file", acq="fmrib0"
        )
    )  # type: ignore
    if len(func_list):
        func_meta = [get_metadata(x) for x in func_list]
        ok &= assert_constant(func_list, func_meta, "ShimSetting", post=post)

    dwi_list: list[str] = layout.get(
        suffix="dwi", extension="nii.gz", return_type="file"
    ) + layout.get(
        suffix="epi", extension="nii.gz", return_type="file", acq="dwib0"
    )  # type: ignore
    if len(dwi_list):
        dwi_meta = [get_metadata(x) for x in dwi_list]
        ok &= assert_constant(dwi_list, dwi_meta, "ShimSetting", post=post)

    return ok


def check_receivecoil(observed: dict, reference: pd.DataFrame) -> bool:
    okay_values = reference.ReceiveCoilActiveElements.unique()
    if not len(okay_values) == 1:
        raise AssertionError(
            "Incorrect options for ReceiveCoilActiveElements in reference"
        )

    return observed.get("ReceiveCoilActiveElements") in okay_values[0]



def check_bvalsbvecs(
    bval_observed: np.ndarray,
    bvec_observed: np.ndarray,
    reference: pd.DataFrame,
    scan: str,
    post: bool = False,
) -> bool:
    """
    in the case of UC scans, we don't get a full dcmstack output in the DWI, so we can't check
    dcmmeta_shape. The length of bvals serves as the check for truncated scans

    root issue seems to be: https://github.com/moloney/dcmstack/issues/51
    """

    rb = np.array(pd.eval(reference["bval"]), dtype=float).squeeze()  # type: ignore
    rv = np.array(pd.eval(reference["bvec"]), dtype=float).squeeze()  # type: ignore

    # in the case of UC scans, we don't get a full dcmstack output in the DWI, so notification must
    # happen
    # root issue seems to be: https://github.com/moloney/dcmstack/issues/51
    if bval_observed.shape[0] < rb.shape[0]:
        print_and_post(
            f"{os.path.basename(scan)} appears truncated", post=post
        )
        ok = False
    elif not (
        np.isclose(rb, bval_observed).all()
        and np.isclose(rv, bvec_observed).all()
    ):
        print_and_post(
            f"{os.path.basename(scan)} has unexpected bvals or bvecs",
            post=post,
        )
        logging.warning(f"bvals: {bval_observed}")
        logging.warning(f"bvecs: {bvec_observed}")
        ok = False
    else:
        ok = True

    return ok


def compare(
    js_observed: str,
    reference: pd.DataFrame,
    post: bool = False,
) -> bool:
    ok = True

    meta = get_metadata(js_observed)

    if reference.scanner.unique()[0] in SIEMENS_W_64:
        if check_receivecoil(meta, reference):
            reference.drop(["ReceiveCoilActiveElements"], axis=1, inplace=True)
        else:
            print_and_post(
                f"{os.path.basename(js_observed)} has unexpected ReceiveCoilActiveElements: {meta.get('ReceiveCoilActiveElements')}",
                post=post,
            )
            ok = False

    # these columns will not be found in any of the jsons. they are mainly indicies used to
    # locate rows in the reference table
    reference.drop(
        ["task", "suffix", "acq", "dir", "scanner", "phantom", "bval", "bvec"],
        axis=1,
        inplace=True,
    )
    js_goal = reference.dropna(axis=1).copy()

    for n in [
        "dcmmeta_affine",
        "dcmmeta_reorient_transform",
        "dcmmeta_shape",
        "SliceTiming",
    ]:
        if n in js_goal.columns.values.tolist():
            js_goal[n] = pd.eval(js_goal.loc[:, n])  # type: ignore

    js_goal = js_goal.to_dict(orient="records")[0]
    observed = {key: meta.get(key) for key in js_goal.keys()}
    observed = remove_translation(observed)

    # These are the parameters
    for epsilon, params in FLOATING_PARAMS.items():
        if any(observed.__contains__(x) for x in params):
            dd1 = DeepDiff(
                {
                    key: js_goal[key]
                    for key in params
                    if js_goal.__contains__(key)
                },
                {
                    key: observed[key]
                    for key in params
                    if js_goal.__contains__(key)
                },
                math_epsilon=epsilon,
                ignore_numeric_type_changes=True,
                ignore_type_subclasses=True,
            )
            if dd1:
                ok = False
                print_and_post(
                    f"json for {os.path.basename(js_observed)} has unexpected values! Checked with threshold {epsilon}!\n"
                    + dd1.pretty(),
                    post=post,
                )

    dd2 = DeepDiff(
        {
            key: js_goal[key]
            for key in js_goal.keys()
            if key not in list(chain(*FLOATING_PARAMS.values()))
        },
        {
            key: observed[key]
            for key in observed.keys()
            if key not in list(chain(*FLOATING_PARAMS.values()))
        },
        ignore_numeric_type_changes=True,
        ignore_type_subclasses=True,
    )

    if dd2:
        print_and_post(
            f"json for {os.path.basename(js_observed)} has unexpected values! Checked with threshold 0\n"
            + dd2.pretty(),
            post=post,
        )
        ok = False
    else:
        print(f"json for {os.path.basename(js_observed)} looks okay")
        ok &= True

    return ok


def getUM(t1w_meta: dict) -> str:
    if t1w_meta.get("DeviceSerialNumber") == "000000000UM750MR":
        site = "UM1"
    elif t1w_meta.get("DeviceSerialNumber") == "0007347633TMRFIX":
        site = "UM2"
    else:
        raise AssertionError("Unsure which UM bids to compare against!")

    return site


def main(
    root: str, site: str, phantom: bool = False, post: bool = False
) -> None:
    ok = 1

    layout = ancpbids.BIDSLayout(root, validate=False)

    if site == "UM":
        any_nii: list[str] = layout.get(extension="nii.gz", return_type="file") # type: ignore
        if len(any_nii) > 0:
            site = getUM(get_metadata(any_nii[0]))
        else:
            raise AssertionError("No scan jsons found")

    reference = pd.read_csv(
        "acq-params.tsv",
        low_memory=False,
        delimiter="\t",
        converters={
            "ImageOrientationPatientDICOM": pd.eval,
            "ImageType": pd.eval,
        },
    ).query("scanner == @site & phantom == @phantom")

    # T1w is easy and _should_ always be present by now. But if it isn't we still don't want the app to
    # fail, so this does a check only if one can be found
    T1ws: list[str] = layout.get(suffix="T1w", extension="nii.gz", return_type="file")  # type: ignore
    if len(T1ws) > 0:
        for scan in T1ws:
            ok *= compare(
                scan,
                reference.query("suffix == 'T1w'").copy(),
                post=post,
            )
    else:
        print_and_post(
            f"No T1w scans found when checking jsons in {pathlib.Path(root).absolute()}",
            post=post,
        )

    for scan in layout.get(
        suffix="dwi", extension="nii.gz", return_type="file"
    ):
        # phantom scans have the DWI split into acq-b1000 and acq-b2000, but there is no
        # acq tag in typical patient scans
        if phantom and (not site == "UM2"):
            acq = re.findall("acq-(b1000|b2000)", scan)
            if len(acq) > 0:
                query = "suffix == 'dwi' & acq == @acq"
                bval_obs = np.genfromtxt(
                    glob(
                        os.path.join(root, "**", "dwi", f"*{acq[0]}*bval"),
                        recursive=True,
                    )[0]
                )
                bvec_obs = np.genfromtxt(
                    glob(
                        os.path.join(root, "**", "dwi", f"*{acq[0]}*bvec"),
                        recursive=True,
                    )[0]
                )
            else:
                # this happens for some (early) SH phantom scans that were collected with the patient protocol
                print_and_post(
                    f"Expected phantom protocol at {root}, but acq-b1000/acq-b2000 not found",
                    post=post,
                )
                query = "suffix == 'dwi'"
                bval_obs = np.genfromtxt(
                    glob(
                        os.path.join(root, "**", "dwi", "*bval"),
                        recursive=True,
                    )[0]
                )
                bvec_obs = np.genfromtxt(
                    glob(
                        os.path.join(root, "**", "dwi", "*bvec"),
                        recursive=True,
                    )[0]
                )
        else:
            query = "suffix == 'dwi'"
            bval_obs = np.genfromtxt(
                glob(os.path.join(root, "**", "dwi", "*bval"), recursive=True)[
                    0
                ]
            )
            bvec_obs = np.genfromtxt(
                glob(os.path.join(root, "**", "dwi", "*bvec"), recursive=True)[
                    0
                ]
            )

        ok *= check_bvalsbvecs(
            bval_observed=bval_obs,
            bvec_observed=bvec_obs,
            reference=reference.query(query).copy(),
            scan=scan, # type: ignore
            post=post,
        )
        ok *= compare(
            scan, # type: ignore
            reference.query(query).copy(), 
            post=post)

    for task in ["rest", "cuff"]:
        for scan in layout.get(
            task=task, extension="nii.gz", return_type="file"
        ):
            if acq := re.findall("(?<=acq-)[a-zA-Z]+", scan):
                query = "suffix == 'bold' & task == @task & acq == @acq"
            else:
                query = "suffix == 'bold' & task == @task"
            ok *= compare(
                scan, # type: ignore
                reference.query(query).copy(),
                post=post,
            )

    for fmap in layout.get(
        extension="nii.gz", return_type="file", suffix="epi"
    ):
        acq = re.findall("acq-(dwib0|fmrib0)", fmap)[0]
        dir = re.findall("dir-(AP|PA)", fmap)[0]  # noqa: F841
        ok &= compare(
            fmap, # type: ignore
            reference.query(
                "suffix == 'epi' & acq == @acq & dir == @dir"
            ).copy(),
            post=post,
        )

    ok *= compare_withinsub(layout, site=site, post=post)
    if not ok:
        logging.warning("Unexpected parameters! See logs")

    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check bids.json files")
    parser.add_argument("root")
    parser.add_argument(
        "site", choices=["NS", "SH", "UC", "UI", "UM", "WS", "RU"]
    )
    parser.add_argument(
        "--phantom", action=argparse.BooleanOptionalAction, default=False
    )
    parser.add_argument(
        "--post", action=argparse.BooleanOptionalAction, default=False
    )

    args = parser.parse_args()
    main(root=args.root, site=args.site, phantom=args.phantom, post=args.post)
