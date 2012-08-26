#!/usr/bin/python

# calls a function with 3 items of the generator (current, next1, next2)
# if next1/next2 wont exist they get the value ""
# the aFunction must look like this func(current, next1, next2)
def lookahead2(iterable, aFunction):
    prev2 = iterable.next()
    prev = iterable.next()
    for item in iterable:
        (ret, jump) = aFunction(iterable, prev2, prev, item)
        for r in ret:
            yield r
        if jump:
            prev2 = iterable.next()
            prev = iterable.next()
        else:
            prev2 = prev
            prev = item
    (ret, jump) = aFunction(iterable, prev, item, "")
    for r in ret:
        yield r
    (ret, jump) = aFunction(iterable, item, "", "")
    for r in ret:
        yield r

def fixReader(iterable, line, line1, line2):
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

def getVal(file, val):
    if val.find("{") != -1 and val.find("}") != -1:
        return val
    if val == "":
        return parse(file)
    return val


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


obj = parse(lookahead2(open("autosave.eu3"), fixReader))

newObj = []
for i in obj:
    if i['key']=='REB':
        for r in i['val']:
            print r['key']
    if i['key'] == 'previous_war':
        continue
    newObj.append(i)

unparse(open("autosave2.eu3", "w"), newObj)
