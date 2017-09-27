import sys
import random

events = []
fixed = []
header = []
with open(sys.argv[1], encoding="utf8") as f:
    isvevent = False
    hasuid = False
    isheader = True
    c = 0
    for line in f:
        c+=1
        if line.startswith("BEGIN:VEVENT"):
            isheader = False
            isvevent = True
            hasuid = False
            fixed.append(line)
        elif line.startswith("END:VEVENT"):
            isvevent = False
            if not hasuid:
                fixed.append("UID:"+''.join(random.choices(string.ascii_uppercase + string.digits, k=N)))
                print("NO UID:"+str(c))
            fixed.append(line)
            events.append(fixed)
            fixed = []
        elif line.startswith("UID:"):
            line = line.replace("@","_at_")
            if hasuid:
                print("MULTIPLE UID:"+str(c))
            else:
                fixed.append(line)
            hasuid = True
        else:
            if isheader:
                header.append(line)
            else:
                fixed.append(line)

for i in range(len(events)):
    with open(sys.argv[1]+"_"+str(i+1)+"_"+".ics", "w", encoding="utf8") as f:
        f.write("".join(header))
        f.write("".join(events[i]))
        f.write("\nEND:VCALENDAR")
