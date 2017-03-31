import django, os, sys, time, resource, re, gc, shutil
from multiprocess import Pool
from functools import partial

from django.utils import timezone
import subprocess

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

    DEBUG = True

    if DEBUG:
        print("  >> Entering add_doc() with document id: "+str(r['UT']))

    django.db.connections.close_all()
    try: # if this doc is in the database, just add to query
        if DEBUG:
            print("     > Document is already in the DB. Add to query table only.")
        doc = Doc.objects.get(UT=r['UT'])
        doc.query.add(q)
        doc.save()
    except: # otherwise, add it!
        if DEBUG:
            print("     > Document is new. Add to doc, query and WoSArticle tables.")
        doc         = Doc(UT=r['UT'])
        doc.title   = get(r,'TI')
        doc.content = get(r,'AB')
        doc.PY      = get(r,'PY')
        doc.save()
        doc.query.add(q)
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

        ## Add authors
        for a in range(len(r['AF'])):
            af = r['AF'][a]
            au = r['AU'][a]
            if 'C1' not in r:               
                r['C1'] = [""]
            a_added = False
            for inst in r['C1']:
                inst = inst.split('] ',1)
                iauth = inst[0]
                try:
                    institute = inst[1]
                    if af in iauth:
                        dai = DocAuthInst(doc=doc)
                        dai.AU = au
                        dai.AF = af
                        dai.institution = institute
                        dai.position = a+1
                        dai.save()
                        a_added = True
                except:
                    pass #TODO Fix this later, these errors are caused by multiline institutions
            if a_added == False:
                dai = DocAuthInst(doc=doc)
                dai.AU = au
                dai.AF = af
                dai.position = a
                dai.save()

############################################################################
############################################################################
## NEW PART TO DEAL WITH REFERENCES

    # Now that the article's saved, we can look at the references....
    # these are in a list accessible by get(r,'CR')
    refs = get(r,'CR')
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
            try: # try and get the doi if it's there
                doi = re.search(", DOI ([^ ]*)",r).group(1)
                doi = re.sub('^\[','',doi) ## This is to deal with lists !! of dois
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
            except: 
                if DEBUG:
                    print("         . No DOI found for this record. Skipping...")
                skip+=1
                pass 
            dr.save() #uncomment this when we want to actually save these

            # Try to get AU, PY & TI
            try: # try and get the fields
                au = str.split(r, ",")[0].strip()
                py = str.split(r, ",")[1].strip()
                so = str.split(r, ",")[2].strip()
    
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
            print("      > Number of references in DB (%)    : "+str(refindb)+" ("+str(skip/len(refs)*100)+"%)")
            print("      > Number of references to scrape (%): "+str(len(doi_lookups_loc))+" ("+str(len(doi_lookups_loc)/len(refs)*100)+"%)")
            print("      > Number of discarded references (%): "+str(skip)+" ("+str(skip/len(refs)*100)+"%)")

            # We can access a documents references by doc.references.all()
            # And get its citations by doc.doc_set.all()

    else :
        print("     > The document has no references!")

    if DEBUG:
        print("  << Exiting add_doc()")
        
#############################################################################
#############################################################################
#############################################################################           
        

def main():
    
    DEBUG    = True
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

    # Open results file and loop over lines
    with open("/queries/"+title+"/results.txt", encoding="utf-8") as res:
        for line in res:
            if '\ufeff' in line: # BOM on first line
                continue
###############################
#### Don't do this parellely anymore, just one at a time is easier here.
            if line=='ER\n':   
                # end of record - add whatever is currently in record
                add_doc(record)
                n_records +=1
                record = {} 
              
                records.append(record)
                continue
            if re.match("^EF",line): #end of file, stop now
                break
            # if the beginning of the line starts with a field key, start a new field
            # otherwise, add whatever is in the line to the current field
            if re.match("(^[A-Z][A-Z1-9])",line): 
                s     = re.search("(^[A-Z][A-Z1-9]) (.*)",line)
                key   = s.group(1).strip()
                value = s.group(2).strip()
                if key in mfields:
                    record[key] = [value]
                else:
                    record[key] = value
            elif len(line) > 1:
                if key in mfields:
                    record[key].append(line.strip())
                else:
                    record[key] += line.strip()
    
    django.db.connections.close_all()
    q.r_count = n_records

    ############ When happy with the script we can uncomment and delete the files again

    #shutil.rmtree("/queries/"+title)
    #os.remove("/queries/"+title+".txt")
    #os.remove("/queries/"+title+".log")

    print("  > Total Number of references processed    : "+str(totnbrefs))
    print("  > Total Number of references in DB (%)    : "+str(totnbrefsindb)+" ("+str(totnbrefsindb/totnbrefs*100)+"%)")
    print("  > Total Number of references to scrape (%): "+str(len(doi_lookups))+" ("+str(len(doi_lookups)/totnbrefs*100)+"%)")
    print("  > Total Number of discarded references (%): "+str(totnbskips)+" ("+str(totnbskips/totnbrefs*100)+"%)")

    q.reftotlen   = totnbrefs
    q.refdblen    = totnbrefsindb
    q.refscraplen = len(doi_lookups)
    q.save()

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
