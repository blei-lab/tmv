import django, os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
import scrapeWoS #import scopus2wosfields
from urllib.parse import urlparse, parse_qsl

print(dir(scrapeWoS))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "BasicBrowser.settings")
django.setup()

from scoping.models import *

def get(r, k):
    try:
        x = r[k]
    except:
        x = ""
    return(x)

def add_doc(r):
    try:
        did = r['di']
        r['UT'] = eid = dict(parse_qsl(urlparse(r['UT']).query))['eid'] 
        django.db.connections.close_all()
        try: # if this doc is in the database, do nothing
            doc = Doc.objects.get(wosarticle__di=did)
            doc.query.add(q)
        except: # otherwise, add it!
            doc = Doc(UT=r['UT'])
            print(doc)
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

            article.save()
            print("article saved")

        
            ## Add authors
            for a in range(len(r['au'])):
                #af = r['AF'][a]
                au = r['au'][a]  
                dai = DocAuthInst(doc=doc)
                dai.AU = au
                dai.position = a
                dai.save()

    except:
        pass
    #print(r)

        
            
        

def main():
    qid = sys.argv[1]

    ## Get query
    global q
    q = Query.objects.get(pk=qid)

    docs = Doc.objects.filter(query=qid)
    for d in docs:
        if len(d.query.all()) == 1:
            d.delete()

    #Doc.objects.filter(query=qid).delete() # doesn't seem like a good idea

    i=0
    n_records = 0
    records=[]
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
                record = {}
                chunk_size+=1
                if chunk_size==max_chunk_size:
                    # parallely add docs
                    pool = Pool(processes=50)
                    pool.map(add_doc, records)
                    #pool.map(partial(add_doc, q=q),records)
                    pool.terminate()
                    records = []
                    chunk_size = 0
                continue
            if re.match("^EF",line): #end of file
                #done!
                break
            if re.match("(^[A-Z][A-Z1-9])(\s*-\s*)",line):
                s = re.search("(^[A-Z][A-Z1-9])(\s*-\s*)(.*)",line)
                key = s.group(1).strip()
                value = s.group(3).strip()
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

    print(chunk_size)

    if chunk_size < max_chunk_size:
        # parallely add docs
        pool = Pool(processes=50)
        pool.map(add_doc, records)
        #pool.map(partial(add_doc, q=q),records)
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
