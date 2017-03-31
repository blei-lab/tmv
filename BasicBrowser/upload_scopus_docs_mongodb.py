import os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
from mongoengine import *
from urllib.parse import urlparse, parse_qsl
connect('mongoengine_documents')

import pymongo
from pymongo import MongoClient
#client = MongoClient()
#db = client.documents
#scopus_docs = db.scopus_docs

class scopus_doc(DynamicDocument):
    scopus_id = StringField(required=True, max_length=50, unique=True)
    PY = IntField(required=True)

#result = db.scopus_docs.create_index([('scopus_id', #pymongo.ASCENDING)],unique=True)

def add_doc(r):
    try:
        d = scopus_doc(**r)
        d.qid = q
        d.save()
    except:
        print("noadd")
        d = scopus_doc.objects.get(scopus_id=r['scopus_id'])
        for f in r:
            d[f] = r[f]
        d.save()

def add_doc_text(r):
    record = {}
    mfields = ['au','AF','CR','C1','References']
    for line in r:
        if re.search("([A-Z][A-Z1-9])(\s{2}-\s*)",line):
            s = re.search("([A-Z][A-Z1-9])(\s{2}-\s*)(.*)",line)
            key = s.group(1).strip()
            value = s.group(3).strip()
            if re.search("(.*)([A-Z][A-Z1-9])(\ {2}-\s*)",value):
                s = re.search("(.*)([A-Z][A-Z1-9])(\s*-\s*)(.*)",value)
                value = s.group(1).strip()
                nextkey = s.group(2).strip()
                nextvalue = s.group(4).strip()
                
                if nextkey in mfields:
                    record[nextkey] = [nextvalue]
                else:
                    record[nextkey] = nextvalue

            if key=="N1":
                s = re.search("([a-zA-Z1-9 ]*): *(.*)",value)
                try:
                    key = s.group(1).strip()
                    value = s.group(2).strip()
                except:
                    print(key)
                    print(value)
            
            if key in mfields:
                record[key] = [value]
            else:
                record[key] = value

        elif len(line) > 1:
            if key in mfields:
                record[key].append(line.strip())
            else:
                record[key] += line.strip()

    try:
        record['scopus_id'] = dict(parse_qsl(urlparse(record['UR']).query))['eid'] 
        add_doc(record)
    except:
        print("don't want to add this record, it has no id!")
        print(record)
        return
    

def add_docs(docs):
    result = db.scopus_docs.insert_many(docs)


def main():
    qid = sys.argv[1]
    global q
    q = qid
    title = str(qid)
    very_par = True
    i=0
    n_records = 0
    records=[]
    if very_par == True:
        record = []
    else:
        record = {}
    mfields = ['au','AF','CR','C1']

    # The bigger the chunk size, the faster it goes, but the more memory it eats!
    max_chunk_size = 10000
    chunk_size = 0

    scopus2WoSFields = {
        'TY': 'dt',
        'TI': 'ti',
        'T2': '',
        'C3': '',
        'J2': 'so',
        'VL': 'vl',
        'IS': '',
        'SP': 'bp',
        'EP': 'ep',
        'PY': 'py',
        'DO': 'di',
        'SN': 'sn',
        'AU': 'au',
        'AD': 'ad',
        'AB': 'ab',
        'KW': 'kwp',
        'Y2': '',
        'CY': '',
        #N1 means we need to read the next bit as key
        'Correspondence Address': '',
        'References': '',
        'UR': 'UT', # use url as ut, that's the only unique identifier...
        'PB': ''
        #'ER': , #End record

    }

    #scopus_doc.objects.delete()

    with open("/queries/"+title+"/s_results.txt", encoding="utf-8") as res:
    #with open("/home/max/Desktop/353/1_scopus.ris", encoding="utf-8") as res:
    #with open("/queries/411/s_results.txt", encoding="utf-8") as res:
        for line in res:
            if n_records > 1000000000:
                break
            if '\ufeff' in line: # BOM on first line
                continue
            if 'ER  -' in line:  
                if not very_par:
                    record['scopus_id'] = dict(parse_qsl(urlparse(record['UR']).query))['eid'] 
                
                # end of record - save it and start a new one
                n_records +=1            
                records.append(record)
                if very_par:
                    record = []
                else:
                    record = {}
                chunk_size+=1
                if chunk_size==max_chunk_size:
                    ## parallely add docs
                    pool = Pool(processes=32)
                    if very_par:
                        pool.map(add_doc_text, records)
                    else:
                        pool.map(add_doc, records)
                    pool.terminate()
                    #result = db.scopus_docs.insert_many(records)
                    records = []
                    chunk_size = 0
                continue
            if re.match("^EF",line): #end of file
                #done!
                #break # We added files together, so there will be multiple EFs
                continue 
            if not very_par:
                if re.search("([A-Z][A-Z1-9])(\s{2}-\s*)",line):
                    s = re.search("([A-Z][A-Z1-9])(\s{2}-\s*)(.*)",line)
                    key = s.group(1).strip()
                    value = s.group(3).strip()
                    if re.search("(.*)([A-Z][A-Z1-9])(\ {2}-\s*)",value):
                        s = re.search("(.*)([A-Z][A-Z1-9])(\s*-\s*)(.*)",value)
                        value = s.group(1).strip()
                        nextkey = s.group(2).strip()
                        nextvalue = s.group(4).strip()
                        
                        if nextkey in mfields:
                            record[nextkey] = [nextvalue]
                        else:
                            record[nextkey] = nextvalue
                    
                    if key in mfields:
                        record[key] = [value]
                    else:
                        record[key] = value

                elif len(line) > 1:
                    if key in mfields:
                        record[key].append(line.strip())
                    else:
                        record[key] += line.strip()
            else:
                record.append(line)

            

    print(chunk_size)

    if chunk_size < max_chunk_size:
        # parallely add docs
        pool = Pool(processes=32)
        if very_par:
            pool.map(add_doc_text, records)
        else:
            pool.map(add_doc, records)
        pool.terminate()
        #result = db.scopus_docs.insert_many(records)

    print(n_records)
    

if __name__ == '__main__':
    t0 = time.time()	
    main()
    totalTime = time.time() - t0

    tm = int(totalTime//60)
    ts = round(totalTime-(tm*60),2)

    

    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")

