import argparse
import re
import json
import pathlib
from typing import List
import zipfile
import datetime

import pandas as pd
import pydicom

from bs4 import BeautifulSoup
from atlassian import Confluence


class Log:
    
    # https://confluence.a2cps.org/display/DOC/Phantom+Log
    site = 'https://confluence.a2cps.org/'
    pageid = "44237591"
    pagetitle = "Phantom Log"

    def __init__(self, bidsroot: pathlib.Path, products: pathlib.Path):
        self.bidsroot = pathlib.Path(bidsroot)
        self.products = pathlib.Path(products)


    def set_session(self, token):
        self.session = Confluence(url=self.site, token=token)


    def set_oldlog(self, cols_to_keep: List[str] = ["site", "date", "notes"]):
        # get current page content
        page = self.session.get_page_by_id(self.pageid, expand='body.storage')
        self._page_content = page.get("body").get("storage").get("value")
        table = pd.read_html(self._page_content)

        # Only one table on the page
        self._oldlog = table[0][cols_to_keep]


    def get_oldlog(self):
        return self._oldlog


    def merge_logs(self):
        # processing serves as base because that builds the most complete list of scans, a list
        # that is based on the files found in /products/<site>/dicoms
        newlog = (
            self.processing
            .merge(self._scans, on=["site", "date"], how="left")
            .merge(self._oldlog, on=["site", "date"], how="left")
        )
        self._newlog = (
            newlog[["site", "date", "notes", "dicom", "bids", "bids_validation", "T1w", "b1000", "b2000", "bold", "id"]]
            .sort_values(by = ["site", "date"])
        )


    def post_log(self):

        soup = BeautifulSoup(self._page_content, 'html.parser')
        soup.table.replace_with(
            BeautifulSoup(
                self._newlog.to_html(index=False, na_rep=""), 
                "html.parser"
            )
        )
        # update page with new content
        self.session.update_page(page_id=self.pageid, title=self.pagetitle, body=str(soup))


    def write_log(self):
        self._newlog.to_csv("phantomlog.tsv", sep="\t", index=False)



    def set_processing(self):

        dicoms = []
        bids = []
        for site in ["NS_northshore", "SH_spectrum_health", "WS_wayne_state", "UI_uic", "UC_uchicago", "UM_umichigan"]:
            # add to dicoms each zip file with QC in the string
            dicoms += [z for z in (self.products / site / "dicoms").glob("*QC*zip")]
            # add to bids list each QC folder that contains the .out file
            bids += [z for z in (self.products / site / "bids").glob("*QC*") if len([x for x in z.glob('*out')]) > 0]

        bids_df = pd.DataFrame({"bids": bids})
        bids_df["id"] = bids_df['bids'].apply(lambda x: x.stem)
        bids_df['bids'] = bids_df['bids'].apply(lambda x: datetime.datetime.fromtimestamp(x.stat().st_ctime).date())
        dicoms_df = pd.DataFrame({"dicom": dicoms})
        
        dicoms_df['date'] = (
            dicoms_df['dicom']
            .apply(self._extract_phantom_date)
            .apply(lambda x: datetime.datetime.strptime(str(x), "%y%m%d").date())
        )
        dicoms_df['id'] = dicoms_df['dicom'].apply(lambda x: x.stem)
        dicoms_df['site'] = self._extract_site(dicoms_df['id'])
        dicoms_df["dicom"] = dicoms_df['dicom'].apply(lambda x: datetime.datetime.fromtimestamp(x.stat().st_ctime).date())
        self.processing = dicoms_df.merge(bids_df, on="id", how="left")
        

    def set_current_scans(self):
        scans = pd.concat(
            [
                pd.read_csv(x, delim_whitespace=True) for x in self.bidsroot.glob("sub-*/ses*/*scans.tsv")
            ],
            ignore_index=True, 
            sort=False
        )
        scans["date"] = pd.to_datetime(scans["acq_time"]).dt.date
        
        scans["site"] = self._extract_site(scans.filename)
        scans["scan"] = scans.filename.str.extract(r"(b1000|b2000|T1w|bold)", expand=False)
        scans.drop(["operator", "acq_time", "randstr", "filename"], axis=1, inplace=True) 
        scans["received"]  = "Y"

        self._scans = (
            scans
            .pivot(index=["site", "date"], columns="scan", values="received")
            .fillna("N")
            .assign(bids_validation = "Y")
        )


    @staticmethod
    def _extract_phantom_date(filename):
        site_zip = zipfile.ZipFile(filename)
        for listing in site_zip.filelist:
            if not listing.is_dir() and not 'DICOMDIR' in listing.filename:
                with site_zip.open(listing) as dcm:
                    header = pydicom.dcmread(dcm, stop_before_pixels=True)
                    break


        day = header.get("AcquisitionDate")
        tmp = datetime.datetime.strptime(day, "%Y%m%d").date()
        return datetime.date.strftime(tmp, "%y%m%d")

    @staticmethod
    def _extract_site(filename: pd.Series):
        return filename.str.extract(r"(ns|ws|sh|ui|uc|um)", expand=False, flags=re.IGNORECASE).str.upper()


def main(bidsroot: pathlib.Path, products: pathlib.Path, post: bool = False) -> None:

    log = Log(bidsroot=bidsroot, products=products)
    log.set_current_scans()
    log.set_processing()
    with open("secrets.json") as j:
        log.set_session(token=json.load(j).get("PAT"))
    log.set_oldlog()
    log.merge_logs()
    log.write_log()

    if post:
       log.post_log()


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--bidsroot', 
        type=pathlib.Path,
        default=pathlib.Path("/corral-secure/projects/A2CPS/resources/imaging/phantom/bids"))
    parser.add_argument(
        '--products', 
        type=pathlib.Path,
        default=pathlib.Path("/corral-secure/projects/A2CPS/products/mris"))
    parser.add_argument(
        '--post', 
        action=argparse.BooleanOptionalAction,
        default="--no-post")

    args = parser.parse_args()
    main(
        bidsroot=args.bidsroot,
        products=args.products,
        post=args.post
    )
