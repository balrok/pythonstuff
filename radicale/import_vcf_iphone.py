import sys
import os



c=0
with open(sys.argv[1], encoding="utf8") as f:
    contact = []
    for line in f:
        line = line.replace("\r","")
        contact += [line]
        if line.startswith("N:"):
            s = line[2:-1].split(";")
            contact += ["FN:"+" ".join([s[1].strip(),s[0].strip()]+s[2:]).strip()+"\n"]
        if line.startswith("END:VCARD"):
            c+=1
            with open(os.path.join(sys.argv[2], "contact_%d.vcf"%c), "w", encoding="utf8") as f2:
                f2.write("".join(contact))
            contact = []
