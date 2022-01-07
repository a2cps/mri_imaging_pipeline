import glob, os, re, argparse, requests
from tempfile import NamedTemporaryFile
from datetime import date
from typing import Union, Optional
import pandas as pd

from atlassian import Confluence

RATING = {
  4: "green",
  3: "green",
  2: "amber",
  1: "red"
}
SCAN = {
  "rest_run-01_bold": "REST1",
  "rest_run-02_bold": "REST2",
  "cuff_run-01_bold": "CUFF1",
  "cuff_run-02_bold": "CUFF2",
  "_T1w": "T1w"
}
LOG_KEYS = {
  "T1 Received": "T1w",
  "fMRI Individualized Pressure Received": "CUFF1",
  "fMRI Standard Pressure Received": "CUFF2",
  "1st Resting State Received": "REST1",
  "2nd Resting State Received": "REST2",
  "DWI Received": "DWI"
}


def read_json(f) -> pd.DataFrame:
  d = pd.read_json(f, orient="index").T
  d.drop('dataset', axis=1, inplace=True)
  print(d)
  d['user'] = re.findall("^[a-z]+", os.path.basename(f))
  d["date"] = date.fromtimestamp(os.path.getmtime(f))
  return d


def get_old_log(s: requests.Session) -> pd.DataFrame:
  r = s.get('https://confluence.a2cps.org/download/attachments/29065229/qc_log.xlsx')
  remote_log = (
    pd.read_excel(r.content)
    .dropna(subset = ["rating"]))  
  remote_log["date"] = [x.date() for x in remote_log["date"]]
  return remote_log


def start_session(token: str, pem: str) -> requests.Session:
  s = requests.Session()
  s.headers.update({"Authorization": f"Bearer {token}"})
  s.verify = pem  
  return s


def main(
  imaging_log, 
  json_dir,
  token: Optional[str] = None, 
  pem: Optional[Union[str, bytes, os.PathLike]] = None) -> None:

  s = start_session(token, pem)

  d = pd.concat([read_json(x) for x in glob.glob(os.path.join(json_dir,"*json"))])
  
  log = (
    pd.read_csv(imaging_log)[["site","subject_id","visit"]+list(LOG_KEYS.keys())]
    .rename(columns={"subject_id": "sub","visit":"ses"})
    .melt(id_vars=["site","sub","ses"], var_name="scan")
    .query("value == 1")
    )
  log['scan'] = [LOG_KEYS[re.findall('|'.join(LOG_KEYS.keys()), x)[0]] for x in log["scan"]]

  old_log = get_old_log(s=s)

  d2 = (
    d
    .assign(
      notes = [", ".join(x) for x in d["artifacts"]],
      sub = [int(re.findall("(?<=sub-)[0-9]{5}", x)[0]) for x in d["subject"]],
      ses = [re.findall("(?<=ses-)[Vv][13]", x)[0] for x in d["subject"]],
      rating = [RATING[int(x)] for x in d["rating"]],
      scan = [SCAN[re.findall('|'.join(SCAN.keys()), x)[0]] for x in d["subject"]]
    )
    .drop(['subject',"artifacts"],axis=1)
    .merge(log, how="outer")
      .merge(
      old_log, 
      on=["site","sub","ses","scan","rating","user","date","notes"],
      how="outer")
  )
  names = ['site','sub', 'ses', 'scan','rating','user','date','notes','followup']

  out = d2[names].sort_values(names)
  out.to_csv("qc_log.tsv", sep="\t", index=False)

  tf = NamedTemporaryFile(suffix=".xlsx")
  out.to_excel(tf, index=False)  

  confluence = Confluence(
    url='https://confluence.a2cps.org',
    cloud=True,
    session=s)

  confluence.attach_file(
    filename=tf.name,
    page_id="29065229", 
    name="qc_log.xlsx", 
    title="QC Log")

  os.remove(tf.name)


if __name__ == '__main__':

  parser = argparse.ArgumentParser(description='update log at https://confluence.a2cps.org/display/DOC/QC+Log')
  parser.add_argument(
    '--imaging_log', 
    default='/corral-secure/projects/A2CPS/shared/urrutia/imaging_report/imaging_log.csv',
    help="log of received scans")
  parser.add_argument(
    '--json_dir', 
    default='/corral-secure/projects/A2CPS/shared/psadil/qclog/mriqc-reviews',
    help="log of received scans")
  parser.add_argument(
    '--token', 
    type=str)
  parser.add_argument(
    '--pem', 
    type=str)

  args = parser.parse_args()
  main(args.imaging_log, args.json_dir, args.token, args.pem)

