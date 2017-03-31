import django, os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial
from urllib.parse import urlparse, parse_qsl

from django.utils import timezone
import subprocess

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

def add_doc(r):

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

    DEBUG    = True

    if DEBUG:
        print("  >> Entering add_doc() with document id: "+str(r['UT']))

    django.db.connections.close_all()
    if Doc.objects.filter(UT=r['UT']).count() == 1:
        doc = Doc.objects.get(UT=r['UT'])
        if DEBUG:
            print("     > Document is already in the DB. Add to query table only.")
        return
        doc.query.add(q)
        doc.save()
    else:   #look for nonexact matches!
        if DEBUG:
            print("     > Looking for nonexact matches.")
        try:
            did = r['DO']    
            if DEBUG:
                print("     > Found a doi!: %s" % did) 
        except:
            did = 'NA'
            pass

        if did=='NA':
            docs = Doc.objects.filter(
                    wosarticle__ti=get(r,'ti')).filter(PY=get(r,'PY')
            )
        else: 
            docs = Doc.objects.filter(wosarticle__di=did)

        if len(docs)==1:
            doc = docs.first()
            doc.query.add(q)
            if DEBUG:
                print("     > Found an exact match!.") 
        if len(docs)>1:
            if DEBUG:
                print("     > Found more than one match (uhoh) Here they are!.") 
            for d in docs:
                print(d.title)
                print(d.UT)
        if len(docs)==0:
            #print("no matching docs")
            if DEBUG:
                print("     > Found no exact matches, computing jaccard similarity for wos docs from same year") 
            s1 = shingle(get(r,'ti'))
            py_docs = Doc.objects.filter(PY=get(r,'PY'))
            docs = []
            for d in py_docs:
                j = jaccard(s1,d.shingle())
                if j > 0.51:
                    d.query.add(q)
                    return
        if len(docs)==0:
            doc = Doc(UT=r['UT'])
            #print(doc)
            doc.title=get(r,'TI')
            doc.content=get(r,'AB')
            doc.PY=get(r,'PY')
            doc.save()
            doc.query.add(q)
            doc.save()
            article = WoSArticle(doc=doc)


            for field in r:
                f = scopus2WoSFields(field)
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


############################################################################
############################################################################
## NEW PART TO DEAL WITH REFERENCES

    print(dir(doc))

    # Now that the article's saved, we can look at the references....
    # these are in a list accessible by get(r,'CR')
    refs = get(r,'References')
    if len(refs) > 0:
        if DEBUG:
            print("     > The document has the following references:")
        skip = 0
        doi_lookups_loc = []
        au_lookups_loc  = []
        py_lookups_loc  = []
        so_lookups_loc  = []
        for r in refs:
            if DEBUG:
                print("       - "+str(r))
            #print(r)
            # Add them to a table of docs to references (a simple table of just the dois)
            dr = DocReferences(doc=doc)
            dr.refall = r
        
            if r[0] == "*":
                if DEBUG:
                    print("         > Skipping (special document)")
                skip+=1
                continue

            # Try to get DOI
            if re.match('(.*)DOI:? (.*)',r):
                DOI = re.search('DOI:? (.*)',r)
                doi = DOI.group(1)
            elif re.match('.*, doi:([^ ]*)',r):
                DOI = re.search(", doi:([^ ]*)",r)
                doi = DOI.group(1)

                dr.refdoi=doi
                if DEBUG:
                    print("         . DOI: "+str(doi))
                #print(doi)
                # Is this document already in our database?????
                doidoc = Doc.objects.filter(wosarticle__di=doi)
                if len(doidoc) > 0:
                    if DEBUG:
                        print("         . DOI exists in DB! Add reference to doc and query2.")
                    doidoc = doidoc.first()
                    doc.references.add(doidoc)
                    doc.save() # If so, create the link already!

                    # Add to query
                    doidoc.query.add(q2)
                    doidoc.save()
    
                else: # otherwise, add it to a list of docs to lookup
                    if DEBUG:
                        print("         . DOI not in DB! Add to lookup list.")
                    doi_lookups.append(doi)
                    doi_lookups_loc.append(doi)                 
            else: 
                if DEBUG:
                    print("         . No DOI found for this record. Skipping...")
                skip+=1
                pass 

            continue
            # Try to get AU, PY & TI
            try: # try and get the fields
                ypat = '(.*?)\(([0-9]{4})[a-z]{0,1}\)(.*)'
                if re.match(ypat,r):
                    s = re.search('(.*?)\(([0-9]{4})[a-z]{0,1}\)(.*)',str(r))
                    tiau = re.split('([A-Z]\.), ',s.group(1))
                    ti = tiau[-1].strip()
                    aul = tiau[0:-1]
                    au = [ ''.join(x) for x in zip(aul[0::2], aul[1::2]) ]
                    py = s.group(2)
                    extra = s.group(3)
                    so = extra.split(',')[0]

                au = ""
                print(ti)    
                flag_problem = False
  
                # Check validity of fields
                test_au = re.match("^([a-zA-Z. ]*)$", au) is not None
                if not test_au:
                    flag_problem = True
                    if DEBUG:
                        print("         . AU doesn't look correct "+" (AU: "+str(au)+")")
                if not py.isdigit():
                    flag_problem = True
                    if DEBUG:
                        print("         . PY field is not a numeric "+" (PY: "+str(py)+")")
                test_so = re.match("^([a-zA-Z0-9&. ]*)$", so) is not None
                if not test_so:
                    flag_problem = True
                    if DEBUG:
                        print("         . SO field doesn't look correct "+" (SO: "+str(so)+")")
#            #dr.refdoi=doi
                if DEBUG:
                    print("         . AU: "+str(au)+"("+str(test_au)+"), PY: "+str(py)+" ("+str(py.isdigit())+") and SO:"+str(so)+" ("+str(test_so)+")")
                if flag_problem:
                    #skip += 1
                    if DEBUG:
                        print("         . Problem with one of the fields. Skipping...")                
                #print(doi)

                # Is this document already in our database?????
                #refdoc = Doc.objects.filter(wosarticle__au=au, wosarticle__py=py, wosarticle__so=so)
  
                #if len(refdoc) > 0:
                #    if DEBUG:
                #        print("         . This reference exists in DB! Add reference to doc and query2.")
                #    refdoc = refdoc.first()
                #    doc.references.add(refdoc)
                #    doc.save() # If so, create the link already!
 
                #    # Add to query
                #    doidoc.query.add(q2)
                #    doidoc.save()

                else: # otherwise, add it to a list of docs to lookup
                    if DEBUG:
                        print("         . This reference is not in DB! Add to lookup lists.")
                    au_lookups.append(au)
                    au_lookups_loc.append(au)
                    py_lookups.append(py)
                    py_lookups_loc.append(py)
                    so_lookups.append(so)
                    so_lookups_loc.append(so)
            except:
                if DEBUG:
                    print("         . Current reference has less than 3 fields. Skipping...")
                #skip+=1
                pass
            dr.save() #uncomment this when we want to actually save these
       
        refindb = len(refs) - skip - len(doi_lookups_loc) 
 
        global totnbrefs
        global totnbrefsindb
        global totnbskips

        totnbrefs     += len(refs)
        totnbrefsindb += refindb
        totnbskips    += skip

        if DEBUG:
            print("      > Number of references              : "+str(len(refs)))
            print("      > Number of discarded references (%): "+str(skip)+" ("+str(skip/len(refs)*100)+"%)")
            print("      > Number of references in DB (%)    : "+str(refindb)+" ("+str(skip/len(refs)*100)+"%)")
            print("      > Number of references to scrape (%): "+str(len(doi_lookups_loc))+" ("+str(len(doi_lookups_loc)/len(refs)*100)+"%)")

            # We can access a documents references by doc.references.all()
            # And get its citations by doc.doc_set.all()

    else :
        print("     > The document has no references!")

    if DEBUG:
        print("  << Exiting add_doc()")

#############################################################################
##

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

    record['UT'] = dict(parse_qsl(urlparse(record['UR']).query))['eid'] 
    add_doc(record)
    try:
        record['UT'] = dict(parse_qsl(urlparse(record['UR']).query))['eid'] 
        #add_doc(record)
    except:
        print("don't want to add this record, it has no id!")
        print(record)
        return
        
#############################################################################
#############################################################################
#############################################################################           
        

def main():
    
    DEBUG = True
    DOI_ONLY = True

    if DEBUG:
        print(">> Entering main() function in upload_docrefs.py")

    # Get query ID from kwargs
    qid  = sys.argv[1] # Query containing list of documents
    q2id = sys.argv[2] # Query containing list of references

    if DEBUG:
        print("  - The document query has the following ID: "+str(qid))
        print("  - The reference query has the following ID: "+str(q2id))

    ## Get queries
    global q
    q = Query.objects.get(pk=qid)
    global q2
    q2 = Query.objects.get(pk=q2id)

    #Doc.objects.filter(query=qid).delete() # doesn't seem like a good idea

    i         = 0
    n_records = 0
    records   = []
    record    = {}
    mfields   = ['AU','AF','CR','C1']

    global doi_lookups # make a list of dois to lookup (global so accessible inside the parallel function)
    global au_lookups
    global py_lookups
    global so_lookups
    global totnbrefs
    global totnbrefsindb
    global totnbskips

    totnbrefs     = 0
    totnbrefsindb = 0
    totnbskips    = 0
 
    doi_lookups   = []
    au_lookups    = []
    py_lookups    = []
    so_lookups    = []


    max_chunk_size = 2000
    chunk_size = 0

    title = str(q.id)

    record = []
    # Open results file and loop over lines
    with open("/queries/"+title+"/s_results.txt", encoding="utf-8") as res:
        for line in res:
            if '\ufeff' in line: # BOM on first line
                continue
###############################
#### Don't do this parellely anymore, just one at a time is easier here.
            if 'ER  -' in line:   # end of record - save it and start a new one                               
                n_records +=1            
                add_doc_text(record)
                record = []
                continue
            if re.match("^EF",line): #end of file
                #done!
                #break # We added files together, so there will be multiple EFs
                continue 
            record.append(line)
    
    django.db.connections.close_all()
    q.r_count = n_records
    q.save()

    ############ When happy with the script we can uncomment and delete the files again

    #shutil.rmtree("/queries/"+title)
    #os.remove("/queries/"+title+".txt")
    #os.remove("/queries/"+title+".log")

    print("  > Total Number of references processed    : "+str(totnbrefs))
    print("  > Total Number of references in DB (%)    : "+str(totnbrefsindb)+" ("+str(totnbrefsindb/totnbrefs*100)+"%)")
    print("  > Total Number of references to scrape (%): "+str(len(doi_lookups))+" ("+str(len(doi_lookups)/totnbrefs*100)+"%)")
    print("  > Total Number of discarded references (%): "+str(totnbskips)+" ("+str(totnbskips/totnbrefs*100)+"%)")

    # Get list of references to look up
    doiset = set(doi_lookups)     # unique values

    if DEBUG:
        print("  - List of references to look up:")
        print(doiset)
    if "DOI" in doiset:
        doiset.remove("DOI") # remove element DOI (if necessary)

    if (len(doiset) > 0):
        # Generate query
        query = 'DO = ("' + '" OR "'.join(doiset) + '")'

        newquery = ''
        if not DOI_ONLY:
            for k in range(1,len(au_lookups)):
                newquery += '(AU=' + str(au_lookups[k]) + ' AND PY=' + str(py_lookups[k]) + ' AND SO="' + str(so_lookups[k]) +'")'
                if k != len(au_lookups):
                    newquery += ' OR '

        if DEBUG:
            print("  - The following query will be sent to the scraper: "+str(query))
            print("  - The following query will be sent to the scraper: "+str(newquery))

        # Save query text
        q2.text = newquery+query
        q2.save()

        ## Now we can write this to a text file and continue......
        # write the query into a text file
        fname = "/queries/"+str(q2id)+".txt"
        with open(fname,"w") as qfile:
            qfile.write(newquery+query)

        if DEBUG:
            print("  - Query written in file: "+str(fname))

    if DEBUG:
        print("<< Exiting main() function in upload_docrefs.py")


if __name__ == '__main__':
    t0 = time.time()	
    main()
    totalTime = time.time() - t0

    tm = int(totalTime//60)
    ts = round(totalTime-(tm*60),2)

    print("done! total time: " + str(tm) + " minutes and " + str(ts) + " seconds")
    print("a maximum of " + str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1000) + " MB was used")
