import django, os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
import scrapeWoS #import scopus2wosfields
from urllib.parse import urlparse, parse_qsl


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from scoping.models import *

def shingle(text):
    return set(s for s in ngrams(text.lower().split(),2))

def get(r, k):
    try:
        x = r[k]
    except:
        x = ""
    return(x)

def jaccard(s1,s2):
    try:
        return len(s1.intersection(s2)) / len(s1.union(s2))
    except:
        return 0

def add_doc_text(r):

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

    record = {}
    mfields = ['au','AF','CR','C1']
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

                try:
                    nextkey = scopus2WoSFields[nextkey]
                except:
                    pass
                
                if nextkey in mfields:
                    record[nextkey] = [nextvalue]
                else:
                    record[nextkey] = nextvalue

            try:
                key = scopus2WoSFields[key]
            except:
                pass
            
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
        record['scopus_id'] = dict(parse_qsl(urlparse(record['UT']).query))['eid'] 
        add_doc(record)
    except:
        print("don't want to add this record, it has no id!")
        print(record)

def add_doc(r):
    django.db.connections.close_all()
    try:
        r['UT'] = dict(parse_qsl(urlparse(r['UT']).query))['eid'] 
    except:
        print(r)
        return

    try:
        did = r['di']     
    except:
        did = 'NA'
        pass

    if did=='NA':
        docs = Doc.objects.filter(
                wosarticle__ti=get(r,'ti')).filter(PY=get(r,'py')
        )
    else: 
        docs = Doc.objects.filter(wosarticle__di=did)

    if len(docs)==1:
        docs.first().query.add(q)
    if len(docs)>1:
        print("more than one doc matching!!!!!")
        for d in docs:
            print(d.title)
            print(d.UT)
    if len(docs)==0:
        #print("no matching docs")
        s1 = shingle(get(r,'ti'))
        py_docs = Doc.objects.filter(PY=get(r,'py'))
        docs = []
        for d in py_docs:
            j = jaccard(s1,d.shingle())
            if j > 0.51:
                d.query.add(q)
                return

    if len(docs)==0:
        doc = Doc(UT=r['UT'])
        #print(doc)
        doc.title=get(r,'ti')
        doc.content=get(r,'ab')
        doc.PY=get(r,'py')
        doc.save()
        doc.query.add(q)
        doc.save()
        article = WoSArticle(doc=doc)


        for field in r:
            f = field.lower()
            try:
                article.f = r[field]
                setattr(article,f,r[field])
                #article.save()
                #print(r[field])
            except:
                print(field)
                print(r[field])

        try:
            article.save()
            
        except:
            pass

    
        ## Add authors
        try:
            dais = []
            for a in range(len(r['au'])):
                #af = r['AF'][a]
                au = r['au'][a]  
                dai = DocAuthInst(doc=doc)
                dai.AU = au
                dai.position = a
                dais.append(dai)
                #dai.save()
            DocAuthInst.objects.bulk_create(dais)
        except:
            print("couldn't add authors")



        
            
        

def main():
    qid = sys.argv[1]

    very_par = True
    ## Get query
    global q
    q = Query.objects.get(pk=qid)

    # delete all docs that only belong to this query
    docs = Doc.objects.filter(query=qid)
    for d in docs:
        if len(d.query.all()) == 1:
            d.delete()


    i=0
    n_records = 0
    records=[]
    if very_par == True:
        record = []
    else:
        record = {}
    mfields = ['au','AF','CR','C1']

    max_chunk_size = 2000
    chunk_size = 0

    print(q.title)

    title = str(q.id)

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

    with open("/queries/"+title+"/s_results.txt", encoding="utf-8") as res:
        for line in res:
            if '\ufeff' in line: # BOM on first line
                continue
            if 'ER  -' in line:   

                # end of record - save it and start a new one
                n_records +=1            
                records.append(record)
                if very_par:
                    record = []
                else:
                    record = {}
                chunk_size+=1
                if chunk_size==max_chunk_size:
                    # parallely add docs
                    pool = Pool(processes=32)
                    if very_par:
                        pool.map(add_doc_text, records)
                    else:
                        pool.map(add_doc, records)
                    pool.terminate()
                    records = []
                    chunk_size = 0
                continue
            if re.match("^EF",line): #end of file
                #done!
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
                        try:
                            nextkey = scopus2WoSFields[nextkey]
                        except:
                            pass
                        
                        if nextkey in mfields:
                            record[nextkey] = [nextvalue]
                        else:
                            record[nextkey] = nextvalue
                    try:
                        key = scopus2WoSFields[key]
                    except:
                        pass
                    
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
    
    django.db.connections.close_all()
    q.r_count = len(Doc.objects.filter(query=q))
    q.save()


    #shutil.rmtree("/queries/"+title)
    #os.remove("/queries/"+title+".txt")
    #os.remove("/queries/"+title+".log")


if __name__ == '__main__':
    t0 = time.time()	
    main()
    totalTime = time.time() - t0

    tm = int(totalTime//60)
    ts = round(totalTime-(tm*60),2)

    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")
