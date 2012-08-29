#!/usr/bin/python

from extension import ExtensionRegistrator

ext = ExtensionRegistrator()
ext.loadFolder('example/') # should end with a /

print "get Extension by name:"
print "----------------------"
for i in ['test1', 'another_test1', 'test2', 'generic']:
    print "%s -> %s" % (i, str(ext.getExtensionByName(i)))

print ""

print "get Extension by regex:"
print "-----------------------"
for i in ['http://www.google.com/?q=123', 'http://www.amazon.com', 'amazon', 'nothing']:
    print "%s -> %s" % (i, str(ext.getExtensionByRegexStringMatch(i)))

