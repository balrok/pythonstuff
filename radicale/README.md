# little scripts to work with radicale

## Import

importing of one large .ics/.vcf file is not possible, so I created small importer scripts

### Import Google ics files into Radicale

Exporting all Google Calendars can be done with: https://support.google.com/calendar/answer/37111
The result is one .ics per calendar.

Those exported calendars are not perfectly suitable for radicale:
    * it has a problem with "@" in the UID
    * Sometimes UID is missing in a VEVENT
    * Sometimes multiple UIDs are inside a VEVENT
    * radicale needs one .ics per VEVENT

#### Usage:

python3 import.py google.ics

Results in google.ics.1.ics, google.ics.2.ics ... one fore each vevent


## birthday

Based on https://github.com/srhnsn/birthday_extractor

Following is in my radicale git-hook
```
#!/bin/bash
CHANGED_CONTACTS=`git diff-tree -r --name-only --no-commit-id master | grep 7808157f-e15c-288f-f103-2e85c002bd79 | wc -l`
echo "POST COMMIT"
echo $CHANGED_CONTACTS

if [[ $CHANGED_CONTACTS -gt 0 ]]; then
    echo "Contacts changed"
    rm collections/collection-root/cmai/2be82432-c6d8-ae01-e76d-cc5778775899/*.ics
    python3 birthday.py -i collections/collection-root/cmai/7808157f-e15c-288f-f103-2e85c002bd79/ -o collections/collection-root/cmai/2be82432-c6d8-ae01-e76d-cc5778775899
fi
```


## Merge Contacts

The vcardlib.py is from https://github.com/mbideau/vcardtools
You give it two folders and it will look for similar items (based on name) - those are merged.. and saved.
The originals are deleted and a symlink is created.

Example call:
* `./contact_diff.py folder1 folder2` will just print out the files for merging and their content
* `./contact_diff.py folder1 folder2 -o new` will store the merged contacts into folder "new"
* `./contact_diff.py folder1 folder2 -o new -s` will store the merged contacts into folder "new", delete originals and place a symlink
