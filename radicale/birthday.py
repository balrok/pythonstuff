import argparse
import datetime
import hashlib
import re
import sys
import os

from icalendar import Calendar, Event


TEMPLATE_ZERO_YEARS = "{name} wird geboren"
TEMPLATE_ONE_YEAR = "{name} wird ein Jahr alt"
TEMPLATE_YEARS = "{name} hat Geburtstag ({age})"
TEMPLATE_YEARS_UNKNOWN = "{name} hat Geburtstag"

NOW = datetime.datetime.now()
CURRENT_YEAR = datetime.date.today().year
START_YEAR = CURRENT_YEAR - 1
END_YEAR = CURRENT_YEAR + 2

ICAL_VERSION = "2.0"
PRODID = "-//Birthday Extractor//Birthday Extractor//EN"


class Birthday:
    def __init__(self, name, year, month, day):
        self.name = name
        self.year = year
        self.month = month
        self.day = day


def add_birthday_events(birthday, cal):
    for cur_year in range(START_YEAR, END_YEAR):
        event = get_birthday_event(birthday, cur_year)
        
        if not event:
            continue
        
        cal.add_component(event)


def generate_calendar(birthdays, multiple = False):
    if multiple:
        cals = []
        for birthday in birthdays:
            for cur_year in range(START_YEAR, END_YEAR):
                event = get_birthday_event(birthday, cur_year)
                if not event:
                    continue
                
                cal = Calendar()
                cal.add("prodid", PRODID)
                cal.add("version", ICAL_VERSION)
                cal.add_component(event)
                cals += [cal]
            
        return cals
    else:
        cal = Calendar()
        
        cal.add("prodid", PRODID)
        cal.add("version", ICAL_VERSION)
        
        for birthday in birthdays:
            add_birthday_events(birthday, cal)
        
        return cal


def get_birthday_event(birthday, cur_year):
    summary = get_summary(birthday, cur_year)
    
    if not summary:
        return
    
    date = datetime.date(cur_year, birthday.month, birthday.day)
    
    m = hashlib.md5()
    m.update(summary.encode("utf-8"))
    uid = m.hexdigest()
    
    event = Event()
    event.add("summary", summary)
    event.add("dtstart", date)
    # No end date, as per http://www.innerjoin.org/iCalendar/all-day-events.html
    #event.add("dtend", date + datetime.timedelta(days=1))
    event.add("dtstamp", NOW)
    event.add("transp", "TRANSPARENT")
    event["uid"] = uid
    
    return event


def get_summary(birthday, cur_year):
    age = cur_year - birthday.year
    
    if age < 0:
        return
    elif age == 0:
        template = TEMPLATE_ZERO_YEARS
    elif age == 1:
        template = TEMPLATE_ONE_YEAR
    elif age > 200:
        template = TEMPLATE_YEARS_UNKNOWN
    else:
        template = TEMPLATE_YEARS
    
    summary = template.format(name=birthday.name, age=age)
    
    return summary


def parse_birthdays(data):
    birthdays = []
    
    vcards = Calendar.from_ical(data, multiple=True)
    
    for vcard in vcards:
        birthday = vcard.get("bday")
        name = vcard.get("fn")
        
        if not birthday:
            continue
        
        match = re.search(r"^(\d{4})\-(\d{2})\-(\d{2})$", birthday)
        
        if not match:
            print("{} has an invalid birthday: {}".format(name, birthday), file=sys.stderr)
            continue
        
        year, month, day = match.groups()
        year, month, day = int(year), int(month), int(day)
        
        birthday = Birthday(name, year, month, day)
        birthdays.append(birthday)
    
    return birthdays


def parse_files(filenames):
    birthdays = []
    
    filenames2 = []
    for filename in filenames:
        if os.path.isdir(filename):
            for i in os.listdir(filename):
                if i.endswith(".vcf"):
                    filenames2 += [os.path.join(filename, i)]
        else:
            filenames2 += [filename]
    for filename in filenames2:
        with open(filename, "r", encoding="utf-8") as fh:
            data = fh.read()
        
        cur_birthdays = parse_birthdays(data)
        birthdays.extend(cur_birthdays)
    
    return birthdays


def main():
    parser = argparse.ArgumentParser(description="Extract birthdays from multiple vCard files into one iCalendar file.")
    parser.add_argument("-i", dest="input", action="append", required=True)
    parser.add_argument("-o", dest="output")
    args = parser.parse_args()
    
    if not os.access(args.output, os.W_OK):
        raise Exception("not writable output directory")
    for i in args.input:
        if not os.access(i, os.R_OK):
            raise Exception("not readable input directory")
    birthdays = parse_files(args.input)
    
    if args.output:
        if os.path.isdir(args.output):
            c=0
            calendars = generate_calendar(birthdays, multiple=True)
            for calendar in calendars:
                c+=1
                output_data = calendar.to_ical()
                with open(os.path.join(args.output, "birthday_"+str(c)+".ics"), "wb") as fh:
                    fh.write(output_data)
            print("Created %d calendars in dir %s" % (c, args.output))
        else:
            calendar = generate_calendar(birthdays)
            output_data = calendar.to_ical()
            with open(args.output, "wb") as fh:
                fh.write(output_data)
            print("Created single calendar in %s" % args.output)
    else:
        calendar = generate_calendar(birthdays)
        output_data = calendar.to_ical()
        print(output_data.decode("utf-8"))


if __name__ == "__main__":
    main()

