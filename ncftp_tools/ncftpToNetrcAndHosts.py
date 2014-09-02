#!/usr/bin/python

import sys
from ncftplib import readBookmarkFile

if len(sys.argv) < 2:
    print """Usage:
./ncftpToNetrcAndHosts.py bookmarks
bookmarks is the the .ncftp/bookmarks file
"""
    sys.exit(1)


bmData = readBookmarkFile(sys.argv[1])
netrcData = ''
hostData = ''
for data in bmData:
    netrcData+="""
machine %s
    login %s
    password %s""" % (data["alias"], data["login"], data["password"])
    newHostString = "\n%s %s" %(data["lastip"], data["alias"])
    newHostString+=" "*(40-len(newHostString))
    newHostString+=" # for .netrc orig host: %s" % (data["host"])
    hostData+=newHostString

print netrcData
print "   "
print hostData

