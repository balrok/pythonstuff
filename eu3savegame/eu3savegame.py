#!/usr/bin/python
import sys
import re

# runs over iterable and then
# calls a function with 3 items of the generator (current, next1, next2)
# if next1/next2 wont exist they get the value ""
# the aFunction must look like this func(current, next1, next2)
# and return (iterable, jump)
# iterable will get yielded and jump says the next item doesn't get used
# this function is not specific to eu3
def lookahead2(iterable, aFunction):
    prev2 = iterable.next()
    prev = iterable.next()
    for item in iterable:
        (ret, jump) = aFunction(prev2, prev, item)
        for r in ret:
            yield r
        if jump:
            prev2 = iterable.next()
            prev = iterable.next()
        else:
            prev2 = prev
            prev = item
    (ret, jump) = aFunction(prev2, prev, "")
    for r in ret:
        yield r
    (ret, jump) = aFunction(prev, "", "")
    for r in ret:
        yield r

# eu3 specific fixer for the fileformat to be easy parsable
def fixReader(line, line1, line2):
    x = line.find("=")
    if x != -1:
        if line.find("=", x+1) != -1:
            # for example: front={15=
            # yields front=
            # {
            # 15=
            return ((line[:x+1], line[x+1:x+2], line[x+3:]), False)
        elif line[x+1:].strip() == "" and line1.find('{') != -1 and line2.find('}') != -1 and line2.strip() != '}' and line2.find("=") == -1:
            # it happened that this exists:
            # setgameplayoptions=
            # {
            # 0 0 0 0 0 0 0 1 0 1 0 0 0 }
            # so we need a lookahead and remove the lookahead from the iterable
            newLine = line.strip() + line1.strip() + line2
            return ((newLine,), True)
        else:
            return ((line,), False)
    else:
        return ((line,), False)

# the basic parse function for those files
# it would work nicely if there were no exceptions inside the file format
def parse(file):
    obj = []
    for line in file:
        line = line.strip()
        x = line.find("=")
        if x != -1:
            key = line[:x]
            val = getVal(file, line[x+1:])
            obj.append({'key':key, 'val':val})
        elif line.find('}') != -1:
            return obj
        else:
            pass #print line
    return obj

# helper for parse
def getVal(file, val):
    if val.find("{") != -1 and val.find("}") != -1:
        return val
    if val == "":
        return parse(file)
    return val

# writes a string into a file in eu3-save format
def unparse(file, obj, depth=0):
    padding = "\t"*depth
    for line in obj:
        val = line['val']
        isArray = isinstance(val, (list))
        if isArray:
            val = ""
        file.write(padding+line['key']+'='+val+"\r\n")
        if isArray:
            file.write(padding+"{\r\n")
            unparse(file, line['val'], depth+1)
            file.write(padding+"}\r\n")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print "usage ./eu3savegame.py sourceSavegame.eu3 > targetSavegame.eu3"
        print "or ./eu3savegame.py sourceSavegame.eu3 targetSavegame.eu3"
        print "Source and Target can't be the same!"
    obj = parse(lookahead2(open(sys.argv[1]), fixReader))

    newObj = []
    # indexes are e,r,t,z
    for e in obj:
        if e['key'] == 'previous_war':
            continue
        if isinstance(e['val'], (list)):
            newEVal = []
            for r in e['val']:
                if r['key'] == 'history':
                    newRVal = []
                    # look into the dates and then delete there everything but the advisors - if no advisors delete the date itself
                    for t in r['val']:
                        if re.match(r"[0-9]{4}\.[0-9]{1,2}\.[0-9]{1,2}", t['key']):
                            newTVal = []
                            for z in t['val']:
                                if z['key'] == 'advisor':
                                    newTVal.append(z)
                            if newTVal:
                                newRVal.append({'key':t['key'],'val':newTVal})
                        else:
                            newRVal.append(t)
                    newEVal.append({'key':r['key'], 'val':newRVal})
                else:
                    newEVal.append(r)
            newE = {'key':e['key'], 'val':newEVal}
        else:
            newE = e
        newObj.append(newE)

    if len(sys.argv) > 2:
        unparse(open(sys.argv[2], "w"), newObj)
    else:
        unparse(sys.stdout, newObj)
