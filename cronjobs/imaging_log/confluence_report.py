import json
import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup 
import subprocess
import os

from output_check import APP_STEPS

def run_bash(bashCommand):
    # #bashCommand = 'curl -H "Authorization: Bearer $TOKEN" https://confluence.a2cps.org/rest/api/content/15929269?expand=body.storage,version  > confluence_response.json'
    # process = subprocess.Popen(bashCommand.split(), stdout=subprocess.PIPE)
    # output, error = process.communicate()
    response = os.system(bashCommand)
    return response


def main():
    #read secrets
    with open('secrets.json') as jsonfile:
        secrets = json.load(jsonfile)
    response = run_bash('curl  --request GET --user "jurrutia@tacc.utexas.edu:{}" --url https://a2cps.atlassian.net/wiki/rest/api/content/5406795?expand=body.storage,version --header "Accept: application/json"  > confluence_response.json'.format(secrets['CONFLUENCE_TOKEN']))
    confluence_page_response = json.load(open('confluence_response.json'))
    html_string = confluence_page_response['body']['storage']['value']
    soup = BeautifulSoup(html_string, 'html.parser')
    tables = pd.read_html(confluence_page_response['body']['storage']['value'])
    confluence_table = tables[0]
    imaging_log = pd.read_csv("report.csv",dtype=str)
    confluence_table.columns = confluence_table.iloc[0]
    confluence_table = confluence_table.drop(index=1)
    confluence_table = confluence_table.drop(index=0)
    confluence_table['id']= confluence_table['site'] + confluence_table['subject_id'].astype(str) + confluence_table['visit']
    imaging_log['id'] = imaging_log['site'] + imaging_log['subject_id'].astype(str) + imaging_log['visit']
    df = pd.merge(imaging_log,confluence_table[['id','Comments']],on = 'id', how='left')
    df['count']=1
    df = df.drop('id', 1)
    #df.index = df.index + 1
    #df.iloc[0] = df.columns
    #df = df.sort_index()
    # add column names as first row
    df = df.T.reset_index().T.reset_index(drop=True)
    df.columns = df.iloc[0]
    df['fMRI T1 Tech Rating'] =	df['fMRI T1 Tech Rating'].replace('1', 1)
    df['Magnet Name'] =	df['Magnet Name'].replace({'1':"Explorer MRI (BIRB)", "2": "Discovery MRI (Modular Unit)"})
    df.fillna('', inplace=True)
    #df['fMRI T1 Tech Rating'] = pd.to_numeric(df['fMRI T1 Tech Rating'])
    df.replace('1','Y', inplace=True)
    df.replace('0','N', inplace=True)

    for col in APP_STEPS:
        df[col] = df[col].replace('2', 'Failed')

    df.drop_duplicates(inplace=True)
    updated_html = df.to_html(header=False,index=False, classes="wrapped relative-table")
    soup_updated_table = BeautifulSoup(updated_html, 'html.parser')
    updated_table = soup_updated_table
    soup.table.replace_with(updated_table)
    updated_page = str(soup)

    confluence_push_json = {
                            "id": "15929269",
                            "type": "page",
                            "title": "Imaging Log",
                            "space": {
                                "id": 3670020,
                                "key": "DOC",
                                "name": "Imaging"
                            },
                            "body": {
                                "storage": {
                                            "representation": "storage"
                                }
                            },
                            "version": {
                                "number": 4
                            }
                            }
    confluence_push_json['version']['number'] = confluence_page_response['version']['number'] + 1
    confluence_push_json['body']['storage']['value'] = updated_page
    with open('confluence_push.json', 'w') as outfile:
        json.dump(confluence_push_json, outfile, indent=4)
    response = run_bash('curl  --request PUT --user "jurrutia@tacc.utexas.edu:{}" --url https://a2cps.atlassian.net/wiki/rest/api/content/5406795 --header "Accept: application/json" --header "Content-Type: application/json" --data "@confluence_push.json"'.format(secrets['CONFLUENCE_TOKEN']))

if __name__ == '__main__':
    main() 