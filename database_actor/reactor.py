from reactors.utils import Reactor, agaveutils
import copy
import sys
import json
import os
import psycopg2
from datetime import datetime
import vbr


def open_connection():
    vbr_user = os.getenv("_vbr_user")
    vbr_host = os.getenv("_vbr_ip")
    vbr_pass = os.getenv("_vbr_pass")

    # conn = psycopg2.connect(
    #     host=vbr_host,
    #     database="a2cps",
    #     user=vbr_user,
    #     password=vbr_pass)
    d = vbr.VBR(config={'ip': vbr_host, 'user': vbr_user, 'pass': vbr_pass, 'db': 'a2cps'})
    return d

def insert_into_table(table, columns, data):
    conn = open_connection()
    cur = conn.cursor()
    # create a '%s' string for every data element, stupid postgres module
    number_of_data_s = ','.join(['%s' for data in data])
    SQL = "INSERT INTO {} ({}) VALUES ({});".format(table,columns,
                                                    number_of_data_s)
    #print(SQL)
    cur = conn.cursor()
    cur.execute(SQL, data)
    #print(cur.query)
    conn.commit()
    return

def get_key_for_table(key_column,table,query_column,query_value):
    conn = open_connection()
    cur = conn.cursor()
    SQL = "SELECT  {} FROM {} WHERE {}='{}';".format(key_column,table,
                                                    query_column,query_value)
    print(SQL)
    # alternatively for likes
    # SELECT  dataset_id FROM dataset WHERE description LIKE 'baseline visit for subject 1';
    # SQL = "SELECT  {} FROM {} WHERE {} LIKE '{}';".format(key_column,table,query_column,query_value)
    cur.execute(SQL)
    key_id = cur.fetchall()
    #print(key_id)
    if key_id == []:
        print("no value found for query: ", SQL)
        return
    if len(key_id) > 1:
        print("multiple mathes for query: ", SQL)
        return key_id
    else:
        # returns list, get first list element and
        # un-tuple-fy it with [0]
        return key_id[0][0]

def write_dataset_entry(data):
    columns = 'data_source,title,description,contained_in' 
    insert_into_table('dataset',columns,data)
    return

def check_and_write_datasets(d,subject_id):
    #subject_id = 'subject_1'
    subject_title = 'subject_' + subject_id
    # subject_dataset_key = get_key_for_table('dataset_id', 'dataset', 'title', 
    #                                         subject_title)
    dataset_description = "dataset for subject " + subject_id
    subject_dataset_key = vbr.VBR.dataset_id_from_description(d, dataset_description)
    if subject_dataset_key is None:
        # make subject datasetkey
        # make visit dataset key
        print('creating subject dataset')
        # data = (1,subject_title,"dataset for subject " + str(subject_id), 1)
        # write_dataset_entry(data)
        # subject_dataset_key = get_key_for_table('dataset_id', 'dataset', 
        #                                         'title', subject_title)
        de = vbr.Dataset(dataset_id=None,data_source=1, title=subject_title, description=dataset_description, contained_in=1)
        d.create_record(de)
        subject_dataset_key = vbr.VBR.dataset_id_from_description(d, dataset_description=dataset_description)
        
    #baseline_visit_protocol_key = get_key_for_table('protocol_id','protocol','name','baseline_visit')
    baseline_visit_protocol_key = vbr.VBR.protocol_id_from_name(d,'baseline_visit')

    baseline_query = 'baseline visit for {}'.format(' '.join(subject_title.split('_')))
    #baseline_visit_dataset_key = get_key_for_table('dataset_id','dataset','description',baseline_query)
    baseline_visit_dataset_key = vbr.VBR.dataset_id_from_description(d, baseline_query)

    if baseline_visit_dataset_key is None:
        # create baseline visit dataset entry
        print('creating baseline visit dataset') 
        # data = (1,"event"+str(baseline_visit_protocol_key) +'_1',"baseline visit for subject " + str(subject_id), subject_dataset_key)
        # write_dataset_entry(data)
        baseline_title = "event" + str(baseline_visit_protocol_key) +'_1'
        baseline_description = "baseline visit for subject " + str(subject_id)
        de = vbr.Dataset(dataset_id=None,data_source=1, title=baseline_title, \
                        description=baseline_description, contained_in=subject_dataset_key)
        d.create_record(de)
        baseline_visit_dataset_key = vbr.VBR.dataset_id_from_description(d, baseline_query)
        
    #image_protocol_key = get_key_for_table('protocol_id','protocol','name','image upload')
    image_protocol_key = vbr.VBR.protocol_id_from_name(d,'image upload')

    return subject_dataset_key, baseline_visit_protocol_key, baseline_visit_dataset_key, image_protocol_key

def write_data_event(protocol_key,rank,subject_id,site_key,dataset_key):
    columns = "protocol,rank,event_ts,event_count,subject,performed_by,status,reason,dataset"
    data = (protocol_key,rank,datetime.now(),1,subject_id,site_key,None,None,dataset_key)
    insert_into_table('data_event',columns,data)
    return

def submit_file_job():
    job_def = copy.copy(r.settings.file_job)

def main():
    """Main function"""
    # create the reactor object
    r = Reactor()
    r.logger.info("Hello this is actor {}".format(r.uid))
    # pull in reactor context
    context = r.context
    print(context)
    # get the message that was sent to the actor
    message = context.message_dict
    # ex UI
    site = message['site']
    subject_id = message['subject_id']
    session = message['session']
    zipfile = message['zipfile']
    outdir = message['outdir']

    d = open_connection()

    # check datasets table for subject and baseline visit entries
    # and write entries if they don't exist
    (subject_dataset_key, baseline_visit_protocol_key, 
    baseline_visit_dataset_key, image_protocol_key) = \
        check_and_write_datasets(d,subject_id)

    # upload event
    #site_key = get_key_for_table('organization_id','organization','name',site)
    # site=UI in this case
    site_key = vbr.VBR.organization_id_from_name(d,site)
    #write_data_event(image_protocol_key,1,subject_id,site_key,baseline_visit_dataset_key)

    de = vbr.DataEvent(data_event_id=None,protocol=image_protocol_key,rank=1, event_ts=datetime.now(),
                        event_count=1,subject=subject_id, performed_by=site_key,
                        status=2,reason=None,dataset=baseline_visit_dataset_key)
    d.create_record(de)
    # submit file entry
    #submit_file_job(zipfile,)
 
    #vbr_read(r)
    # iso_timestamp = datetime.datetime.utcnow().isoformat(timespec='seconds')
    # filename_timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


if __name__ == '__main__':
    main()
