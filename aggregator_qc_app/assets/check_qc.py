import re
import argparse
import requests
from pathlib import Path
from datetime import date
from typing import Optional
import tempfile
import xml.etree.ElementTree as ET

import pandas as pd
import numpy as np

from atlassian import Confluence

SCAN = {
    "rest_run-01_bold": "REST1",
    "rest_run-02_bold": "REST2",
    "cuff_run-01_bold": "CUFF1",
    "cuff_run-02_bold": "CUFF2",
    "_T1w": "T1w",
    "dwi": "DWI",
}

TASK_THRESH = {"rest": 0.3, "cuff": 0.9}


def _zscore(scores: np.array) -> np.array:
    return (scores - scores.mean()) / scores.std()


def _format_url(url: str, text: str = "link") -> str:
    return f'<a href="{url}">{text}</a>'


def read_json(f: Path) -> pd.DataFrame:
    d = pd.read_json(f, orient="index").T
    d.drop("dataset", axis=1, inplace=True)
    d["source"] = re.findall("^[a-z]+", f.name)
    d["date"] = date.fromtimestamp(f.stat().st_mtime)
    return d


def post_notification(
    notification: str, confluence: Optional[Confluence] = None
) -> None:
    if confluence is not None:
        confluence.update_page(
            page_id="25755998",
            title="QC Aggregation",
            body=notification,
            parent_id=None,
            type="page",
            representation="storage",
            minor_edit=True,
        )
    else:
        print(notification)
    return


def build_notification(outliers: pd.DataFrame, notification) -> str:
    for site, small in outliers.sort_index().groupby(level=0):
        notification.append(f"<h3>{site}</h3>")
        for idx, row in small.sort_index().iterrows():
            if row.source in ["technologist", "auto"]:
                notification.append(
                    f'<p><strong>{idx[-1]}: {row.drop(["rating","notes","date","source"]).dropna().to_dict()}</strong></p>'
                )
            else:
                notification.append(
                    f'<p>{idx[-1]}: {row.drop(["rating","notes","date","source"]).dropna().to_dict()}</p>'
                )

    return "\n".join(notification)


def build_bids_name(d: pd.DataFrame, suffix: str) -> pd.DataFrame:
    if suffix == "bold":
        d["task"] = np.select(
            [
                [bool(re.search(x.scan, "REST1")) for x in d.itertuples()],
                [bool(re.search(x.scan, "REST2")) for x in d.itertuples()],
                [bool(re.search(x.scan, "CUFF1")) for x in d.itertuples()],
                [bool(re.search(x.scan, "CUFF2")) for x in d.itertuples()],
            ],
            ["rest", "rest", "cuff", "cuff"],
        )
        d["run"] = np.select(
            [
                [bool(re.search(x.scan, "REST1")) for x in d.itertuples()],
                [bool(re.search(x.scan, "REST2")) for x in d.itertuples()],
                [bool(re.search(x.scan, "CUFF1")) for x in d.itertuples()],
                [bool(re.search(x.scan, "CUFF2")) for x in d.itertuples()],
            ],
            ["01", "02", "01", "02"],
        )
        d["bids_name"] = [
            f"sub-{x.sub}_ses-{x.ses}_task-{x.task}_run-{x.run}_{suffix}"
            for x in d.itertuples()
        ]
    elif suffix in ["T1w", "dwi"]:
        d["bids_name"] = [f"sub-{x.sub}_ses-{x.ses}_{suffix}" for x in d.itertuples()]

    return d


def get_outliers(
    d: pd.DataFrame,
    groups,
    url_root: str = "https://a2cps.org/workbench/data/tapis/projects/a2cps.project.PHI-PRODUCTS/mris",
    imaging_log: Path = Path(
        "/corral-secure/projects/A2CPS/shared/urrutia/imaging_report/imaging_log.csv",
    ),
) -> pd.DataFrame:
    """
    get_outliers(fname=pd.read_csv('group_T1w.tsv', delimiter="\t"))
    get_outliers(fname=pd.read_csv('group_T1w.tsv', delimiter="\t"), ['site'])
    """
    SITE_CODES = {
        "UI": "UI_uic",
        "NS": "NS_northshore",
        "UC": "UC_uchicago",
        "UM": "UM_umichigan",
        "WS": "WS_wayne_state",
        "SH": "SH_spectrum_health",
    }

    sites = (
        pd.read_csv(imaging_log, usecols=["subject_id", "site"])
        .rename(columns={"subject_id": "sub"})
        .drop_duplicates()
    )
    dind = d[["bids_name"]].copy()
    dind["sub"] = [int(re.findall("\d{5}", x)[0]) for x in dind["bids_name"]]
    dind["ses"] = [re.findall("ses-([a-zA-Z0-9]+)", x)[0] for x in dind["bids_name"]]

    if "task" in groups:
        indices = ["site", "sub", "task", "ses", "bids_name"]
        dind["task"] = [re.findall("task-(\w+)_", x)[0] for x in dind["bids_name"]]
    else:
        indices = ["site", "sub", "ses", "bids_name"]

    dind = dind.merge(sites, on="sub", how="left")

    d.drop(d.filter(regex="spacing.*|size.*").columns, axis=1, inplace=True)
    outliers = (
        d.merge(dind, on=["bids_name"])
        .set_index(indices)
        .groupby(groups)
        .transform(lambda x: np.where(np.abs(_zscore(x)) > 3, x, np.nan))
        .dropna(how="all")
        .round(1)
    )
    outliers["url"] = [
        f"{url_root}/{SITE_CODES[site]}/mriqc/{site}{sub}{ses}"
        for site, sub, ses in zip(
            outliers.index.get_level_values("site"),
            outliers.index.get_level_values("sub"),
            outliers.index.get_level_values("ses"),
        )
    ]
    outliers["url"] = outliers.apply(lambda x: _format_url(x.url), axis=1)

    return outliers


def gather_dwi(root: Path = Path("/corral-secure/projects/A2CPS/products/mris")):
    d = (
        pd.concat(
            [
                pd.read_csv(x)
                for x in root.glob(
                    "*/qsiprep/*/qsiprep/sub*/ses*/dwi/*_desc-ImageQC_dwi.csv"
                )
            ]
        )
        .rename(columns={"file_name": "bids_name"})
        .drop(
            columns=[
                "subject_id",
                "acq_id",
                "task_id",
                "dir_id",
                "space_id",
                "rec_id",
                "session_id",
                "run_id",
            ]
        )
    )
    return d


def extract_iqr(xml: Path) -> float:
    f = ET.parse(xml)
    iqr = float(f.getroot().find("qualityratings/IQR").text)
    return 105 - 10 * iqr


def extract_defects(xml: Path) -> float:
    f = ET.parse(xml)
    n = float(f.getroot().find("qualitymeasures").find("SurfaceEulerNumber").text)
    return 2 - 2 * n


def build_cat_df(xml: Path) -> pd.DataFrame:
    rating = "green"
    iqr = extract_iqr(xml)
    defects = extract_defects(xml)
    # defect threshold from Table 3 of Rosen et al. 2018; 10.1016/j.neuroimage.2017.12.059
    if iqr < 60 or defects < -217:
        rating = "red"
    elif iqr < 80:
        rating = "yellow"
    d = pd.DataFrame(
        [
            {
                "sub": int(re.findall("\d{5}", str(xml))[0]),
                "ses": re.findall("(?<=ses-)[Vv][13]", str(xml))[0],
                "scan": "T1w",
                "rating": rating,
                "source": "auto",
                "date": date.fromtimestamp(xml.stat().st_ctime),
            }
        ]
    )
    return d


def gather_cat(root: Path = Path("/corral-secure/projects/A2CPS/products/mris")):
    return pd.concat([build_cat_df(x) for x in root.glob("*/cat12/*/report/*xml")])


def gather_motion(
    root: Path = Path("/corral-secure/projects/A2CPS/products/mris"),
) -> pd.DataFrame:
    confounds = []
    for s in [
        "NS_northshore",
        "SH_spectrum_health",
        "UC_uchicago",
        "UI_uic",
        "UM_umichigan",
        "WS_wayne_state",
    ]:
        for task in ["rest", "cuff"]:
            for tsv in (root / s / "fmriprep").glob(
                f"{s[0:2]}*/{task}/fmriprep/sub*/ses*/func/*confounds_timeseries.tsv"
            ):
                rmsd = pd.read_csv(
                    tsv, sep="\t", usecols=["rmsd"], dtype={"rmsd": np.float64}
                )
                # current version of fmriprep strips leading 0, so for matching later need to add it back
                bids_name_raw = re.search(
                    r"sub-\w+_ses-\w+_task-\w+_run-\d+", str(tsv)
                ).group(0)
                confounds.append(
                    pd.DataFrame(
                        {
                            "bids_name": bids_name_raw[0:-1] + "0" + bids_name_raw[-1] + "_bold",
                            "fd_mean": rmsd.mean(),
                            "fd_max": rmsd.max(),
                            "fd_perc": np.mean(rmsd.to_numpy() > TASK_THRESH[task]),
                            "n_trs": len(rmsd),
                        }
                    )
                )

    return pd.concat(confounds, ignore_index=True)


def auto_rate_bold_scan(row) -> str:
    if (row.fd_mean > 0.55) or (row.n_trs < 450):
        rating = "red"
    elif (row.fd_mean > 0.25) or (row.fd_perc > 0.2) or (row.fd_max > 5):
        rating = "yellow"
    else:
        rating = "green"

    return rating


def rate_motion(d: pd.DataFrame) -> pd.DataFrame:
    bold_iqm = gather_motion()
    bold_iqm["rating"] = [auto_rate_bold_scan(x) for x in bold_iqm.itertuples()]
    rated = d.merge(bold_iqm[["bids_name", "rating"]], on="bids_name", how="left").drop(
        ["bids_name"], axis=1
    )
    rated["source"] = "auto"
    # fmriprep processing often lags. default assumes scan is okay
    rated["rating"] = rated["rating"].fillna("green")
    return rated


def start_session(token: str, pem: Path) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}"})
    s.verify = str(pem)
    return s


def source_to_code(src) -> int:
    if src in ["auto", "technologist"]:
        out = 0
    else:
        out = 1
    return out


def rating_to_code(src) -> int:
    if src == "green":
        out = 3
    elif src == "yellow":
        out = 2
    else:
        out = 1
    return out


def rate_dwi(
    d: pd.DataFrame,
    root: Path = Path("/corral-secure/projects/A2CPS/products/mris"),
) -> pd.DataFrame:
    DWI_LENGTHS = {
        "NS": [102],
        "SH": [103],
        "UC": [102],
        "UI": [104],
        "UM": [104],
        "WS": [102],
    }

    bvals = (
        pd.concat(
            [
                pd.read_csv(x, header=None, delim_whitespace=True).T.assign(
                    f=x.absolute()
                )
                for x in root.glob(
                    "*/bids/*/sub*/ses-V*/dwi/*bval"
                )  # V is ses for excluding phantoms
            ]
        )
        .groupby("f")
        .count()
        .reset_index()
        .rename(columns={0: "observed"})
    )
    bvals["site"] = [
        re.findall("|".join(DWI_LENGTHS.keys()), str(x))[0] for x in bvals["f"]
    ]
    bvals = bvals.merge(
        pd.DataFrame.from_dict(DWI_LENGTHS, orient="index", columns=["expected"])
        .reset_index()
        .rename(columns={"index": "site"})
    )
    bvals["rating"] = bvals.apply(
        lambda row: "green" if row["expected"] == row["observed"] else "red", axis=1
    )
    bvals["sublong"] = bvals.apply(
        lambda x: re.findall("[A-Z]{2}\d{5}V[13]", str(x["f"]))[0],
        axis=1,
    )
    d["sublong"] = d.apply(lambda row: f'{row["site"]}{row["sub"]}{row["ses"]}', axis=1)
    d["source"] = "auto"
    return d.merge(bvals[["rating", "sublong"]], on="sublong").drop(["sublong"], axis=1)


def write_ratings_unique(
    d: pd.DataFrame,
    outdir: Path = Path("/corral-secure/projects/A2CPS/shared/urrutia/imaging_report"),
) -> pd.DataFrame:

    # manual ratings always overwrite auto + tech scans
    d["source_code"] = [source_to_code(x) for x in d["source"].values]

    # of the auto scans, always take the lowest
    d["rating_grade"] = [rating_to_code(x) for x in d["rating"].values]

    # if multiple grades remain, take the most recent
    # currently there are no dates for tech ratings. this hack of fake date is to ensure that they stay
    # selecting the most recent rating
    d["date"] = pd.to_datetime(d["date"])
    d.loc[pd.isnull(d["date"]), "date"] = pd.to_datetime("2000-01-01")

    single_rating = (
        d.groupby(["site", "sub", "ses", "scan"], as_index=False)
        .apply(lambda x: x[x["source_code"] == x["source_code"].max(skipna=False)])
        .groupby(["site", "sub", "ses", "scan"], as_index=False)
        .apply(lambda x: x[x["rating_grade"] == x["rating_grade"].min(skipna=False)])
        .groupby(["site", "sub", "ses", "scan"], as_index=False)
        .apply(lambda x: x[x["date"] == x["date"].max(skipna=False)])
        .drop(["source_code", "rating_grade"], axis=1)
    )
    single_rating.loc[
        single_rating["date"] == pd.to_datetime("2000-01-01"), "date"
    ] = pd.to_datetime("")
    single_rating["date"] = single_rating["date"].copy().dt.date
    single_rating.to_csv(outdir / "qc-log-latest.csv", index=False)

    return single_rating


def update_qclog(
    imaging_log: Path,
    json_dir: Path,
    outdir: Path,
    token: Optional[str] = None,
    pem: Optional[Path] = None,
) -> pd.DataFrame:
    RATING = {"4": "green", "3": "green", "2": "yellow", "1": "red", "0": ""}
    LOG_KEYS = {
        "T1 Received": "T1w",
        "fMRI Individualized Pressure Received": "CUFF1",
        "fMRI Standard Pressure Received": "CUFF2",
        "1st Resting State Received": "REST1",
        "2nd Resting State Received": "REST2",
        "DWI Received": "DWI",
    }

    log = (
        pd.read_csv(imaging_log)[
            ["site", "subject_id", "visit", "fMRI T1 Tech Rating"]
            + list(LOG_KEYS.keys())
        ]
        .rename(
            columns={
                "subject_id": "sub",
                "visit": "ses",
                "fMRI T1 Tech Rating": "rating",
            }
        )
        .melt(id_vars=["site", "sub", "ses", "rating"], var_name="scan")
        .query("value == 1")
        .drop(["value"], axis=1)
    )
    log["scan"] = [
        LOG_KEYS[re.findall("|".join(LOG_KEYS.keys()), x)[0]] for x in log["scan"]
    ]
    log["rating"].fillna(0, inplace=True)
    log["rating"] = log.apply(
        lambda row: str(int(row["rating"])) if row["scan"] == "T1w" else "0", axis=1
    )
    log["source"] = log.apply(
        lambda row: "technologist" if row["scan"] == "T1w" else "", axis=1
    )
    log["rating"] = [RATING[x] for x in log["rating"]]
    log_t1w = log.query("scan in ['T1w']")
    log_dwi = rate_dwi(
        log.query("scan in ['DWI']").copy().drop(["rating", "source"], axis=1)
    )
    log_bold = rate_motion(
        d=build_bids_name(log.query("not scan in ['DWI','T1w']").copy(), "bold").drop(
            ["rating", "source", "task", "run"], axis=1
        )
    )
    log_short = log_t1w[["site", "sub"]].drop_duplicates()

    # gather_cat doesn't have access to site, hence merging
    log_cat = gather_cat().merge(log_short)

    log_all = pd.concat([log_bold, log_t1w, log_dwi, log_cat])

    d = pd.concat([read_json(x) for x in json_dir.glob("*json")])
    d2 = (
        d.assign(
            notes=[", ".join(x) for x in d["artifacts"]],
            sub=[int(re.findall("\d{5}", x)[0]) for x in d["subject"]],
            ses=[re.findall("(?<=ses-)[Vv][13]", x)[0] for x in d["subject"]],
            rating=[RATING[str(x)] for x in d["rating"]],
            scan=[SCAN[re.findall("|".join(SCAN.keys()), x)[0]] for x in d["subject"]],
        )
        .drop(["subject", "artifacts"], axis=1)
        .merge(log_short)
        .merge(log_all, how="outer")
        .query("rating!=''")
    )
    names = ["site", "sub", "ses", "scan", "rating", "source", "date", "notes"]
    to_upload = d2[names].sort_values(names)

    if token is not None:
        confluence = Confluence(
            url="https://confluence.a2cps.org",
            cloud=True,
            session=start_session(token, pem),
        )
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as f:
            to_upload.to_excel(f.name, index=False, engine="openpyxl")
            confluence.attach_file(
                filename=f.name, page_id="29065229", name="qc_log.xlsx", title="QC Log"
            )
    else:
        print(to_upload)

    return write_ratings_unique(to_upload.copy(), outdir=outdir)


def main(
    t1w_fname: Path,
    bold_fname: Path,
    json_dir: Path,
    imaging_log: Path = Path(
        "/corral-secure/projects/A2CPS/shared/urrutia/imaging_report/imaging_log.csv",
    ),
    outdir: Path = Path("/corral-secure/projects/A2CPS/shared/urrutia/imaging_report"),
    token: Optional[str] = None,
    pem: Optional[Path] = None,
) -> None:

    qclog = update_qclog(
        imaging_log=imaging_log,
        json_dir=json_dir,
        token=token,
        pem=pem,
        outdir=outdir,
    )

    qclog_anat = build_bids_name(
        qclog.query("scan=='T1w'").drop(["scan"], axis=1).copy(), "T1w"
    ).set_index(["site", "sub", "ses", "bids_name"])

    qclog_func = (
        build_bids_name(
            qclog.query("scan in ['CUFF1', 'CUFF2', 'REST1', 'REST2']").copy(), "bold"
        )
        .drop(["run", "scan"], axis=1)
        .set_index(["site", "sub", "task", "ses", "bids_name"])
    )

    anat_outliers = get_outliers(
        d=pd.read_csv(t1w_fname, delimiter="\t"),
        groups=["site"],
        imaging_log=imaging_log,
    ).join(qclog_anat)
    func_outliers = get_outliers(
        d=pd.read_csv(bold_fname, delimiter="\t"),
        groups=["site", "task"],
        imaging_log=imaging_log,
    ).join(qclog_func)
    dwi_outliers = get_outliers(
        d=gather_dwi(), groups=["site"], imaging_log=imaging_log
    )
    dwi_outliers["source"] = ""
    dwi_outliers["rating"] = pd.NA
    dwi_outliers["notes"] = ""
    dwi_outliers["date"] = ""

    anat_notification = build_notification(anat_outliers, ["<h1>T1w</h1>"])
    func_notification = build_notification(func_outliers, ["<h1>bold</h1>"])
    dwi_notification = build_notification(dwi_outliers, ["<h1>dwi</h1>"])

    header = """
  <ul>
    <li> This page is generated automatically and so manual edits will be overwritten.</li>
    <li> Scans are listed here if they are flagged as being an outlier (which does not necessarily indicate poor quality). </li>
    <li> Unreviewed scans should be reviewed, and the review should be logged by adding review jsons to TACC. </li>
  </ul>
  """

    notification = "".join(
        [
            header,
            f'<p>{_format_url("https://a2cps.org/workbench/data/tapis/projects/a2cps.project.PHI-PRODUCTS/mris/all_sites/mriqc-group", text="group htmls")}</p>',
            anat_notification,
            func_notification,
            dwi_notification,
        ]
    )

    if token is not None:
        post_notification(
            notification,
            Confluence(
                url="https://confluence.a2cps.org",
                cloud=True,
                session=start_session(token, pem),
            ),
        )
    else:
        post_notification(notification)

    return


if __name__ == "__main__":

    """
    python check_qc.py group_T1w.tsv group_bold.tsv --token "$(<.token)"
    """

    parser = argparse.ArgumentParser(
        description="check mriqc-group output for outliers"
    )
    parser.add_argument(
        "t1w_fname",
        default="group_T1w.tsv",
        help="group level tsv for T1w images",
        type=Path,
    )
    parser.add_argument(
        "bold_fname",
        default="group_bold.tsv",
        help="group level tsv for bold images",
        type=Path,
    )
    parser.add_argument(
        "--imaging_log",
        default="/corral-secure/projects/A2CPS/shared/urrutia/imaging_report/imaging_log.csv",
        help="log of received scans",
        type=Path,
    )
    parser.add_argument(
        "--json_dir",
        default="/corral-secure/projects/A2CPS/shared/psadil/qclog/mriqc-reviews",
        help="log of received scans",
        type=Path,
    )
    parser.add_argument("--token", type=str)
    parser.add_argument(
        "--pem", default=Path("confluence-a2cps-org-chain.pem"), type=Path
    )
    parser.add_argument(
        "--outdir",
        help="Location to deposit qc-log-latest.csv, which has one rating per scan",
        default=Path("/corral-secure/projects/A2CPS/shared/urrutia/imaging_report"),
        type=Path,
    )

    args = parser.parse_args()
    main(
        args.t1w_fname,
        args.bold_fname,
        json_dir=args.json_dir,
        token=args.token,
        pem=args.pem,
        imaging_log=args.imaging_log,
        outdir=args.outdir,
    )
