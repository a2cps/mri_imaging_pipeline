import argparse
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import atlassian
import numpy as np
import polars as pl
import requests
from tapipy import tapis

SCAN = {
    "rest_run-01_bold": "REST1",
    "rest_run-02_bold": "REST2",
    "cuff_run-01_bold": "CUFF1",
    "cuff_run-02_bold": "CUFF2",
    "_T1w": "T1w",
    "dwi": "DWI",
}

TASK_THRESH = {"rest": 0.3, "cuff": 0.9}

PEM = Path("/opt/confluence-a2cps-org-chain.pem")
DEFAULT_CACHED_CLIENT = Path.home() / ".tapis3" / "client.json"

SITE_CODES = {
    "UI": "UI_uic",
    "NS": "NS_northshore",
    "UC": "UC_uchicago",
    "UM": "UM_umichigan",
    "WS": "WS_wayne_state",
    "SH": "SH_spectrum_health",
    "RU": "RU_rush",
}

CONFLUENCE_URL = "https://a2cps.atlassian.net"
A2CPS = Path("/corral-secure/projects/A2CPS")
MRIS = A2CPS / "products" / "mris"
ILOG = A2CPS / "shared" / "urrutia" / "imaging_report" / "imaging_log.csv"


@dataclass
class ConfluenceAuth:
    username: str
    token: str


def zscore_expr(col_name: str):
    return (pl.col(col_name) - pl.col(col_name).mean()) / pl.col(col_name).std()


def load_cached_client(src: Path) -> dict:
    with open(src, "r") as f:
        data = json.load(f)
    return data


def check_client(cached_client: Path) -> None:
    if not cached_client.exists():
        msg = f"""
        Uploading requires a cached client, but one was not found. 
        Searched at {cached_client}.
        """
        raise AssertionError(msg)


def get_client(
    cached_client: Path = DEFAULT_CACHED_CLIENT,
) -> tapis.Tapis:
    check_client(cached_client)

    client = load_cached_client(cached_client)
    t = tapis.Tapis(
        base_url=client.get("base_url"),
        tenant_id=client.get("tenant_id"),
        access_token=client.get("access_token"),
        refresh_token=client.get("refresh_token"),
        client_id=client.get("client_id"),
        client_key=client.get("client_key"),
        verify=True,
    )  # type: ignore
    return t


def get_confluence_token(
    secret_name: str, cached_client: Path = DEFAULT_CACHED_CLIENT
) -> str:
    client = get_client(cached_client=cached_client)

    token: tapis.TapisResult = client.sk.readSecret(  # type: ignore
        secretType="user",
        secretName=secret_name,
        tenant=os.environ.get("_tapisTenant"),
        user=os.environ.get("_tapisEffectiveUserId"),
    )
    pat: str | None = token.get("secretMap").get("token")  # type: ignore
    if pat is None:
        msg = "unable to find key 'token' in secretMap"
        raise AssertionError(msg)

    return pat


def _format_url(url: str, text: str = "link") -> str:
    return f'<a href="{url}">{text}</a>'


def read_mriqc_manual_json(f: Path) -> pl.DataFrame:
    """read manual review jsons

    Args:
        f (Path): _description_

    Returns:
        pl.DataFrame: _description_
    """
    source_match = re.findall("^[a-zA-Z]+", f.name)
    source = source_match[0] if source_match else ""

    return (
        pl.read_json(f)
        .drop("dataset", strict=False)
        .with_columns(
            pl.col("rating").cast(pl.Int64),
            source=pl.lit(source),
            date=pl.lit(date.fromtimestamp(f.stat().st_mtime)),
            f=pl.lit(f.name),
        )
    )


def post_notification(
    notification: str, confluence_auth: ConfluenceAuth | None = None
) -> None:
    if confluence_auth is not None:
        confluence = atlassian.Confluence(
            url=CONFLUENCE_URL,
            session=start_session(confluence_auth=confluence_auth),
        )
        confluence.update_page(
            page_id="5406790",
            title="QC Aggregation",
            body=notification,
            parent_id=None,
            type="page",
            representation="storage",
            minor_edit=True,
        )
    else:
        print(notification)


def build_notification(outliers: pl.DataFrame, notification: list) -> str:
    if outliers.is_empty():
        return "\n".join(notification)

    sites = outliers["site"].unique().sort()

    for site in sites:
        small = outliers.filter(pl.col("site") == site).sort(
            ["sub", "ses", "bids_name"]
        )
        notification.append(f"<h3>{site}</h3>")

        for row in small.iter_rows(named=True):
            bids_name = row["bids_name"]

            # Filter out keys and None/NaN values
            content = {
                k: v
                for k, v in row.items()
                if k
                not in [
                    "rating",
                    "notes",
                    "date",
                    "source",
                    "site",
                    "sub",
                    "ses",
                    "bids_name",
                    "task",
                ]
                and v is not None
                and (not isinstance(v, float) or not np.isnan(v))
            }

            if row.get("source") in ["technologist", "auto"]:
                notification.append(f"<p><strong>{bids_name}: {content}</strong></p>")
            else:
                notification.append(f"<p>{bids_name}: {content}</p>")

    return "\n".join(notification)


def build_bids_name(d: pl.DataFrame, suffix: str) -> pl.DataFrame:
    if suffix == "bold":
        d = d.with_columns(
            task=pl.when(pl.col("scan").str.contains("REST1"))
            .then(pl.lit("rest"))
            .when(pl.col("scan").str.contains("REST2"))
            .then(pl.lit("rest"))
            .when(pl.col("scan").str.contains("CUFF1"))
            .then(pl.lit("cuff"))
            .when(pl.col("scan").str.contains("CUFF2"))
            .then(pl.lit("cuff"))
            .otherwise(pl.lit(None)),
            run=pl.when(pl.col("scan").str.contains("REST1"))
            .then(pl.lit("01"))
            .when(pl.col("scan").str.contains("REST2"))
            .then(pl.lit("02"))
            .when(pl.col("scan").str.contains("CUFF1"))
            .then(pl.lit("01"))
            .when(pl.col("scan").str.contains("CUFF2"))
            .then(pl.lit("02"))
            .otherwise(pl.lit(None)),
        ).with_columns(
            bids_name=pl.format(
                "sub-{}_ses-{}_task-{}_run-{}_{}",
                pl.col("sub"),
                pl.col("ses"),
                pl.col("task"),
                pl.col("run"),
                pl.lit(suffix),
            )
        )
    elif suffix in ["T1w", "dwi"]:
        d = d.with_columns(
            bids_name=pl.format(
                "sub-{}_ses-{}_{}", pl.col("sub"), pl.col("ses"), pl.lit(suffix)
            )
        )
    return d


def get_outliers(
    d: pl.DataFrame, groups: list[str], imaging_log: Path = ILOG
) -> pl.DataFrame:
    """
    get_outliers(fname=pl.read_csv('group_T1w.tsv', separator="\t"))
    get_outliers(fname=pl.read_csv('group_T1w.tsv', separator="\t"), ['site'])
    """

    sites = (
        pl.read_csv(imaging_log, columns=["subject_id", "site"])
        .rename({"subject_id": "sub"})
        .unique()
    )

    d = d.with_columns(
        sub=pl.col("bids_name").str.extract(r"(\d{5})").cast(pl.Int64),
        ses=pl.col("bids_name").str.extract(r"ses-([a-zA-Z0-9]+)"),
    )

    if "task" in groups:
        d = d.with_columns(task=pl.col("bids_name").str.extract(r"task-(\w+)_"))

    d = d.join(sites, on="sub", how="left")

    # Drop regex columns
    cols_to_drop = [
        c
        for c in d.columns
        if re.match(r"spacing.*|size.*|.*dimension.*|.*num_directions|.*max_b", c)
    ]
    d = d.drop(cols_to_drop)

    # Identify numeric columns for z-score
    numeric_cols = [
        c
        for c, t in d.schema.items()
        if t in [pl.Float64, pl.Int64, pl.Float32, pl.Int32]
        and c not in groups + ["sub", "ses", "bids_name"]
    ]

    # Calculate outliers
    # Keep value if zscore > 3, else null
    exprs = [
        pl.when((zscore_expr(c).abs() > 3).over(groups))
        .then(pl.col(c))
        .otherwise(pl.lit(None))
        .alias(c)
        for c in numeric_cols
    ]

    keys = ["site", "sub", "ses", "bids_name"] + (["task"] if "task" in groups else [])

    outliers = d.select(keys + exprs)

    # Drop rows where all numeric columns are null (not outliers)
    outliers = outliers.filter(
        pl.any_horizontal([pl.col(c).is_not_null() for c in numeric_cols])
    ).with_columns([pl.col(c).round(1) for c in numeric_cols])

    return outliers


def gather_dwiqc(root: Path = MRIS):
    dfs: list[pl.DataFrame] = []
    for x in root.glob("*/qsiprep/*/qsiprep/sub*/ses*/dwi/*_desc-ImageQC_dwi.csv"):
        df = pl.read_csv(x)
        dfs.append(df)

    if not dfs:
        raise AssertionError("No dwi qc files found")

    d = (
        pl.concat(dfs, how="vertical_relaxed")
        .rename({"file_name": "bids_name"})
        .drop(
            [
                "subject_id",
                "acq_id",
                "task_id",
                "dir_id",
                "space_id",
                "rec_id",
                "session_id",
                "run_id",
            ],
            strict=False,
        )
    )
    return d


def extract_iqr(xml: Path) -> float:
    f = ET.parse(xml)
    iqr = float(f.getroot().find("qualityratings/IQR").text)  # type: ignore
    return 105 - 10 * iqr


def extract_defects(xml: Path) -> float:
    f = ET.parse(xml)
    n = float(
        f.getroot().find("qualitymeasures").find("SurfaceEulerNumber").text  # type: ignore
    )
    return 2 - 2 * n


def build_cat_df(xml: Path) -> pl.DataFrame:
    rating = 3
    iqr = extract_iqr(xml)
    defects = extract_defects(xml)
    # defect threshold from Table 3 of Rosen et al. 2018; 10.1016/j.neuroimage.2017.12.059
    if iqr < 60 or defects < -217:
        rating = 1
    elif iqr < 80:
        rating = 2
    d = pl.DataFrame(
        {
            "sub": int(re.findall(r"\d{5}", str(xml))[0]),
            "ses": re.findall("(?<=ses-)[Vv][13]", str(xml))[0],
            "scan": "T1w",
            "rating": rating,
            "source": "auto",
            "date": date.fromtimestamp(xml.stat().st_ctime),
        }
    )
    return d


def gather_cat(root: Path = MRIS):
    dfs = [build_cat_df(x) for x in root.glob("*/cat12-v4/*/cat12/report/*xml")]
    if not dfs:
        raise AssertionError("did not find any cat12 data frames?")
    return pl.concat(dfs)


def get_task(src: Path) -> str:
    maybe_task = re.findall("rest|cuff", src.name)
    if not len(maybe_task):
        msg = f"Unable to find task id in {src}"
        raise RuntimeError(msg)
    return maybe_task[0]


def gather_motion(root: Path = MRIS) -> pl.DataFrame:
    confounds = []
    for s in SITE_CODES.values():
        for tsv in (root / s / "fmriprep").glob(
            f"{s[0:2]}*/fmriprep/sub*/ses*/func/*confounds_timeseries.tsv"
        ):
            rmsd = pl.read_csv(
                tsv, separator="\t", columns=["rmsd"], null_values="n/a"
            ).select(pl.col("rmsd").cast(pl.Float64))
            bids_name = tsv.name.replace("desc-confounds_timeseries.tsv", "bold")
            task = get_task(tsv)
            confounds.append(
                pl.DataFrame(
                    {
                        "bids_name": [bids_name],
                        "fd_mean": [rmsd["rmsd"].mean()],
                        "fd_max": [rmsd["rmsd"].max()],
                        "fd_perc": [(rmsd["rmsd"] > TASK_THRESH[task]).mean()],
                        "n_trs": [rmsd.height],
                    }
                )
            )

    return pl.concat(confounds)


def rate_rest2_wo_cuff(d: pl.DataFrame) -> pl.DataFrame:
    red_rest2 = (
        d.select(["sub", "ses", "scan"])
        .with_columns(value=pl.lit(1))
        .unique()
        .pivot(on="scan", index=["sub", "ses"], values="value")
        .with_columns(
            rating_new=pl.when(
                (pl.col("REST2") == 1)
                & pl.col("CUFF2").is_null()
                & pl.col("CUFF1").is_null()
            )
            .then(1)
            .otherwise(3)
        )
        .filter(pl.col("rating_new") == 1)
        .select(["sub", "ses", "rating_new"])
        .with_columns(scan=pl.lit("REST2"))
    )

    return (
        d.join(red_rest2, on=["sub", "ses", "scan"], how="left")
        .with_columns(rating=pl.coalesce(["rating_new", "rating"]))
        .drop("rating_new")
    )


def rate_bold(d: pl.DataFrame) -> pl.DataFrame:
    bold_iqm = gather_motion().with_columns(
        rating=pl.when((pl.col("fd_mean") > 0.55) | (pl.col("n_trs") < 450))
        .then(1)
        .when(
            (pl.col("fd_mean") > 0.25)
            | (pl.col("fd_perc") > 0.2)
            | (pl.col("fd_max") > 5)
        )
        .then(2)
        .otherwise(3)
    )

    rated = (
        d.join(bold_iqm.select(["bids_name", "rating"]), on="bids_name", how="left")
        .drop("bids_name")
        .with_columns(source=pl.lit("auto"))
    )

    rated = rate_rest2_wo_cuff(rated)
    return rated


def start_session(
    confluence_auth: ConfluenceAuth,
) -> requests.Session:
    s = requests.Session()
    s.auth = (confluence_auth.username, confluence_auth.token)
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
    ilog: pl.DataFrame, dwiqc: pl.DataFrame, root: Path = MRIS
) -> pl.DataFrame:
    DWI_LENGTHS = {
        "NS": 102,
        "SH": 103,
        "UC": 102,
        "UI": 104,
        "UM": 104,
        "WS": 102,
        "RU": 103,
    }

    bval_counts = []
    for x in root.glob("*/bids/*/sub*/ses-V*/dwi/*bval"):
        with open(x, "r") as f:
            content = f.read().strip().split()
            count = len(content)
            bval_counts.append({"f": str(x.absolute()), "observed": count})

    if not bval_counts:
        raise AssertionError("No bvals found")

    bvals = pl.DataFrame(bval_counts).with_columns(
        site=pl.col("f").str.extract(r"({})".format("|".join(DWI_LENGTHS.keys())))
    )

    expected_df = pl.DataFrame(
        [{"site": k, "expected": v} for k, v in DWI_LENGTHS.items()]
    )

    bvals = (
        bvals.join(expected_df, on="site", how="left")
        .with_columns(
            rating_acq=pl.when(pl.col("expected") == pl.col("observed"))
            .then(3)
            .otherwise(1),
            sub=pl.col("f").str.extract(r"(\d{5})").cast(pl.Int64),
            ses=pl.col("f").str.extract(r"(V[13])"),
        )
        .select("sub", "ses", "rating_acq")
    )

    dwiqc = (
        dwiqc.with_columns(
            sub=pl.col("bids_name").str.extract(r"sub-(\d{5})").cast(pl.Int64),
            ses=pl.col("bids_name").str.extract(r"ses-([Vv][13])"),
        )
        .join(ilog, on=["sub", "ses"], how="left")
        .with_columns(
            raw_percent_bad_slices=pl.col("raw_num_bad_slices")
            / (pl.col("raw_dimension_z") * pl.col("raw_num_directions"))
            * 100,
        )
        .with_columns(
            rating_ndc=pl.when(pl.col("raw_masked_neighbor_corr") > 0.6)
            .then(3)
            .when(pl.col("raw_masked_neighbor_corr") > 0.4)
            .then(2)
            .otherwise(1),
            rating_bad_slices=pl.when(pl.col("raw_percent_bad_slices") < 1)
            .then(3)
            .when(pl.col("raw_percent_bad_slices") < 10)
            .then(2)
            .otherwise(1),
            rating_contrast=pl.when(pl.col("raw_dwi_contrast") > 1.3)
            .then(3)
            .when(pl.col("raw_dwi_contrast") > 1.1)
            .then(2)
            .otherwise(1),
        )
        .with_columns(
            rating_metrics=pl.min_horizontal(pl.selectors.starts_with("rating_"))
        )
        .select("sub", "ses", "rating_metrics")
        .join(bvals, on=["sub", "ses"], how="right")
        .with_columns(rating=pl.min_horizontal(pl.selectors.starts_with("rating_")))
    )
    return (
        ilog.join(dwiqc, on=["sub", "ses"], how="left")
        .fill_null(3)  # any missing ratings will get 3 => green
        .with_columns(source=pl.lit("auto"))
    )


def write_ratings_unique(d: pl.DataFrame) -> pl.DataFrame:
    fake_date = date(2000, 1, 1)

    # manual ratings always overwrite auto + tech scans
    d = d.with_columns(
        source_code=pl.col("source").map_elements(
            source_to_code, return_dtype=pl.Int64
        ),
        rating_grade=pl.col("rating").map_elements(
            rating_to_code, return_dtype=pl.Int64
        ),
        date=pl.col("date").cast(pl.Date, strict=False),
    ).with_columns(pl.col("date").fill_null(fake_date))

    window = ["site", "sub", "ses", "scan"]

    d = (
        d.filter(pl.col("source_code") == pl.col("source_code").max().over(window))
        .filter(pl.col("rating_grade") == pl.col("rating_grade").min().over(window))
        .filter(pl.col("date") == pl.col("date").max().over(window))
    ).drop(["source_code", "rating_grade"])

    # Restore null date
    d = d.with_columns(
        pl.when(pl.col("date") == fake_date)
        .then(None)
        .otherwise(pl.col("date"))
        .alias("date")
    )

    d.write_csv("qc-log-latest.csv")

    return d


def get_manual_reviews(root: Path) -> pl.DataFrame:
    # Read manual review jsons
    djs: list[pl.DataFrame] = []
    for f in root.glob("*json"):
        djs.append(read_mriqc_manual_json(f))

    if not len(djs):
        raise AssertionError("No manual reviews found")

    return (
        pl.concat(djs, how="diagonal_relaxed")
        .with_columns(
            notes=pl.col("artifacts").map_elements(
                lambda x: ", ".join(x), return_dtype=pl.Utf8
            ),
            sub=pl.col("f").str.extract(r"sub-(\d{5})").cast(pl.Int64),
            ses=pl.col("f").str.extract(r"ses-([Vv][13])"),
            scan=pl.col("f")
            .str.extract(r"({})".format("|".join(SCAN.keys())))
            .replace(SCAN),
        )
        .select("sub", "ses", "scan", "rating", "notes", "date")
    )


def update_qclog(imaging_log: Path, json_dir: Path) -> pl.DataFrame:
    # all ratings will start as numeric and map to the traffic light
    # before returning

    LOG_KEYS = {
        "T1 Received": "T1w",
        "fMRI Individualized Pressure Received": "CUFF1",
        "fMRI Standard Pressure Received": "CUFF2",
        "1st Resting State Received": "REST1",
        "2nd Resting State Received": "REST2",
        "DWI Received": "DWI",
    }

    log = (
        pl.read_csv(
            imaging_log,
            columns=["site", "subject_id", "visit", "fMRI T1 Tech Rating"]
            + list(LOG_KEYS.keys()),
        )
        .rename(
            {
                "subject_id": "sub",
                "visit": "ses",
                "fMRI T1 Tech Rating": "rating",
            }
        )
        .unpivot(
            index=["site", "sub", "ses", "rating"],
            variable_name="scan",
            value_name="acquired",
        )
        .filter(pl.col("acquired") == 1)
        .drop("acquired")
        .with_columns(pl.col("scan").replace(LOG_KEYS))
        .with_columns(
            rating=pl.when(pl.col("scan") == "T1w")
            .then(pl.col("rating").cast(pl.Int64).cast(pl.String))
            .otherwise(None),
            source=pl.when(pl.col("scan") == "T1w")
            .then(pl.lit("technologist"))
            .otherwise(pl.lit("")),
        )
    )

    log_t1w = log.filter(pl.col("scan") == "T1w")

    log_dwi = rate_dwi(
        log.filter(pl.col("scan") == "DWI").drop(["rating", "source"]),
        dwiqc=gather_dwiqc(),
    )

    log_bold = rate_bold(
        d=build_bids_name(
            log.filter(~pl.col("scan").is_in(["DWI", "T1w"])), "bold"
        ).drop(["rating", "source", "task", "run"])
    )

    sub_site_maps = log.select(["site", "sub"]).unique()

    log_cat = gather_cat().join(sub_site_maps, on="sub", how="left")
    log_manual = get_manual_reviews(json_dir).join(sub_site_maps, on="sub", how="left")

    combined = pl.concat(
        [log_bold, log_t1w, log_dwi, log_cat, log_manual], how="diagonal_relaxed"
    )

    return combined.select(
        ["site", "sub", "ses", "scan", "rating", "source", "date", "notes"]
    ).with_columns(
        pl.col("rating").replace(
            {4: "green", 3: "green", 2: "yellow", 1: "red", 0: None}
        )
    )


def upload_to_confluence(qclog: pl.DataFrame, auth: ConfluenceAuth | None) -> None:
    if auth is not None:
        confluence = atlassian.Confluence(
            url=CONFLUENCE_URL,
            session=start_session(confluence_auth=auth),
        )
        with tempfile.NamedTemporaryFile(suffix=".xlsx") as f:
            qclog.write_excel(f.name)
            confluence.attach_file(
                filename=f.name,
                page_id="5406798",
                name="qc_log.xlsx",
                title="QC Log",
            )
    else:
        print(qclog)


def build_overall_notification(
    qclog: pl.DataFrame,
    t1w_fname: Path,
    bold_fname: Path,
    imaging_log: Path,
) -> str:
    qclog_anat = build_bids_name(
        qclog.filter(pl.col("scan") == "T1w").drop("scan"), "T1w"
    )

    qclog_dwi = build_bids_name(
        qclog.filter(pl.col("scan") == "DWI").drop("scan"), "dwi"
    )

    qclog_func = build_bids_name(
        qclog.filter(pl.col("scan").is_in(["CUFF1", "CUFF2", "REST1", "REST2"])),
        "bold",
    ).drop(["run", "scan"])

    anat_outliers = get_outliers(
        d=pl.read_csv(t1w_fname, separator="\t"),
        groups=["site"],
        imaging_log=imaging_log,
    ).join(qclog_anat, on=["site", "sub", "ses", "bids_name"], how="left")

    dwi_outliers = get_outliers(
        d=gather_dwiqc(), groups=["site"], imaging_log=imaging_log
    ).join(qclog_dwi, on=["site", "sub", "ses", "bids_name"], how="left")

    func_outliers = get_outliers(
        d=pl.read_csv(bold_fname, separator="\t"),
        groups=["site", "task"],
        imaging_log=imaging_log,
    ).join(qclog_func, on=["site", "sub", "task", "ses", "bids_name"], how="left")

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

    return "".join(
        [
            header,
            f"<p>{_format_url('https://a2cps.org/workbench/data/tapis/projects/a2cps.project.PHI-PRODUCTS/mris/all_sites/mriqc-group', text='group htmls')}</p>",
            anat_notification,
            func_notification,
            dwi_notification,
        ]
    )


def main(
    t1w_fname: Path,
    bold_fname: Path,
    json_dir: Path,
    imaging_log: Path = ILOG,
    confluence_auth: ConfluenceAuth | None = None,
) -> None:
    qclog = update_qclog(imaging_log=imaging_log, json_dir=json_dir)

    # this is a table of all ratings that have been provided for each scan
    upload_to_confluence(qclog, confluence_auth)

    # save log with one rating per scan (this is mainly what gets used)
    qclog_unique = write_ratings_unique(qclog)

    notification = build_overall_notification(
        qclog_unique,
        t1w_fname=t1w_fname,
        bold_fname=bold_fname,
        imaging_log=imaging_log,
    )

    post_notification(notification=notification, confluence_auth=confluence_auth)


if __name__ == "__main__":
    """
    python check_qc.py group_T1w.tsv group_bold.tsv --token "$(<.token)"
    """

    parser = argparse.ArgumentParser(
        description="check mriqc-group output for outliers"
    )
    parser.add_argument(
        "--t1w_fname",
        default=MRIS / "all_sites" / "mriqc" / "group_T1w.tsv",
        help="group level tsv for T1w images",
        type=Path,
    )
    parser.add_argument(
        "--bold_fname",
        default=MRIS / "all_sites" / "mriqc" / "group_bold.tsv",
        help="group level tsv for bold images",
        type=Path,
    )
    parser.add_argument(
        "--imaging_log", default=ILOG, help="log of received scans", type=Path
    )
    parser.add_argument(
        "--json_dir",
        default=A2CPS / "shared" / "psadil" / "qclog" / "mriqc-reviews",
        help="log of received scans",
        type=Path,
    )
    parser.add_argument("--secret-name", type=str)
    parser.add_argument("--confluence-username", type=str)
    parser.add_argument("--cached-client", type=Path, default=DEFAULT_CACHED_CLIENT)

    args = parser.parse_args()

    if args.secret_name:
        check_client(args.cached_client)
        if not args.confluence_username:
            msg = "Received secret_name but no username. Unable to access confluence without username"
            raise ValueError(msg)
        confluence_auth = ConfluenceAuth(
            username=args.confluence_username,
            token=get_confluence_token(
                secret_name=args.secret_name, cached_client=args.cached_client
            ),
        )
    else:
        confluence_auth = None

    main(
        args.t1w_fname,
        args.bold_fname,
        json_dir=args.json_dir,
        imaging_log=args.imaging_log,
        confluence_auth=confluence_auth,
    )
