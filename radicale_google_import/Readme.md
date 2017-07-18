# Import Google ics files into Radicale

Exporting all Google Calendars can be done with: https://support.google.com/calendar/answer/37111
The result is one .ics per calendar.

Those exported calendars are not perfectly suitable for radicale:
    * it has a problem with "@" in the UID
    * Sometimes UID is missing in a VEVENT
    * Sometimes multiple UIDs are inside a VEVENT
    * radicale needs one .ics per VEVENT

## Usage:

python3 import.py google.ics

Results in google.ics.1.ics, google.ics.2.ics ... one fore each vevent
