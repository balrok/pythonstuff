#!/usr/bin/python

import sys
import csv

if len(sys.argv) < 2:
    print """Usage:
./ncftpToNetrcAndHosts.py bookmarks [netrc] [hosts]
bookmarks is the the .ncftp/bookmarks file
if netrc and/or hosts is not specified everything goes to stdout
"""
    sys.exit(1)


bmarks = open(sys.argv[1])
netrcData = ''
hostData = ''
i = 0
for line in bmarks:
    i+=1
    if i<=2:
        # skip first two lines as they contain only metadata
        continue
    reader = csv.reader([line], skipinitialspace=True)
    for r in reader:
        alias = r[0]
        host = r[1]
        login = r[2]
        password = r[3][9:].decode("base64").rstrip("\0")
        directory = r[5]
        port = r[7]
        lastchange = r[8]
        lastip = r[13]
        netrcData+="""
machine %s
    login %s
    password %s""" % (alias, login, password)
        newHostString = "\n%s %s" %(lastip, alias)
        newHostString+=" "*(40-len(newHostString))
        newHostString+=" # for .netrc orig host: %s" % (host)
        hostData+=newHostString

print netrcData
print "   "
print hostData

