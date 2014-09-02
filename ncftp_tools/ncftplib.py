import csv

def readBookmarkFile(bm_filename):
    bmarks = open(bm_filename)

    data = []

    i = 0
    for line in bmarks:
        i+=1
        if i<=2:
            # skip first two lines as they contain only metadata
            continue
        reader = csv.reader([line], skipinitialspace=True)
        for r in reader:
            data.append({
                "alias": r[0],
                "host": r[1],
                "login": r[2],
                "password": r[3][9:].decode("base64").rstrip("\0"),
                "directory": r[5],
                "port": r[7],
                "lastchange": r[8],
                "lastip": r[13],
            })
    return data
