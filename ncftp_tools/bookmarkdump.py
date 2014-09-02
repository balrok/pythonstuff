#!/usr/bin/python

import sys
from ncftplib import readBookmarkFile

if len(sys.argv) < 2:
    print """Usage:
./ncftpToNetrcAndHosts.py bookmarks [entry_name] [entry_name2]
bookmarks is the the .ncftp/bookmarks file
specify an entry name (the alias) to just print a single one
or specify multiple entry names to print them
"""
    sys.exit(1)


bmData = readBookmarkFile(sys.argv[1])
printOnlyAlias = []
if len(sys.argv) > 2:
    printOnlyAlias = sys.argv[2:]

if printOnlyAlias != []:
    print "only dumping: " + ",".join(printOnlyAlias)

def printEntry(data):
    connectDirectory = data["directory"]
    if len(connectDirectory) == 0 or connectDirectory[0] != "/":
        connectDirectory = "/" + connectDirectory
    print """Alias: {alias}
-------{0}
    Host:       {host}:{port}
    Username:   {login}
    Password:   {password}
    Folder:     {directory}
    lastchange: {lastchange}
    lastip:     {lastip}
    Connector:  ftp://{login}:{password}@{host}:{port}{1}
    """.format(len(data["alias"])*"-", connectDirectory, **data)



for data in bmData:
    if printOnlyAlias != [] and data["alias"] not in printOnlyAlias:
        continue
    printEntry(data)
