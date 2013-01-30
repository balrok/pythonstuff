#!/usr/bin/python
# from https://github.com/Rotmg/Rotmg

import urllib2
import os
import sys

uo = urllib2.urlopen("http://realmofthemadgod.appspot.com/picture/list",'dataType=2&guid=administrator%40wildshadow%2Ecom&myGUID=D9C87C410C4711DB3757A6C42F919D00331C3273&num=2400&offset=0&ignore=193370')

from lxml import etree

d = uo.read()
print d
root = etree.fromstring(d)


for pic in root.xpath("//Pic"):
    id = pic.get("id")
    name= pic.find("PicName").text

    fn = os.path.join(os.path.dirname(sys.argv[0]),"pics","%s.png" % id)
    if not os.path.exists(fn):
        print "Fetching %s" % id
        o = urllib2.urlopen("http://realmofthemadgod.appspot.com/picture/get",'id=%s&ignore=123123' % id)
        with open(fn,"wb") as f:
            f.write(o.read())
    print id,name


import Image

# normalize all images to 32x32 pic - the size which is used inside the game client
for pic in root.xpath("//Pic"):
    id = pic.get("id")
    name= pic.find("PicName").text
    fn = os.path.join(os.path.dirname(sys.argv[0]),"pics","%s.png" % id)
    fn_rescale = os.path.join(os.path.dirname(sys.argv[0]),"pics","%s_rescale.png" % id)
    if os.path.exists(fn) and not os.path.exists(fn_rescale):
        im1 = Image.open(fn)
        im2 = im1.resize((32, 32), Image.NEAREST)
        im2.save(fn_rescale)
