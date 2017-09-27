#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import vobject
import argparse
import os
import shlex

import vcardlib
vcardlib.OPTION_MATCH_APPROX_SAME_FIRST_LETTER = False
vcardlib.OPTION_MATCH_APPROX_STARTSWITH = False
vcardlib.OPTION_MATCH_APPROX_RATIO = 90
vcardlib.OPTION_MATCH_APPROX_MIN_LENGTH = 5
vcardlib.OPTION_MATCH_APPROX_MAX_DISTANCE = range(-3, 3)

def main():
    parser = argparse.ArgumentParser(description="Compare two folders containing vcards")
    parser.add_argument(dest="input", nargs=2)
    parser.add_argument(dest="output", nargs="?")
    parser.add_argument("-s", dest="symlink", action="store_true")
    args = parser.parse_args()
    print(args.input)
    print(args.output)
    changes = run(*args.input)
    if args.output:
        changes = write_changes(args.output, changes)
    if args.symlink:
        if not args.output:
            raise Exception("Symlink only when output")
        write_symlinks(changes)

def write_symlinks(changes):
    for obj in changes:
        new = obj["new_filename"]
        old = obj["filenames"]
        for f in old:
            print("rm "+shlex.quote(f))
            print("ln -s "+shlex.quote(os.path.abspath(new))+" "+shlex.quote(f))
            #os.remove(f)
        

def write_changes(out_dir, changes):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    for obj in changes:
        vcard = obj["vcard"]
        # collect names
        available_names = vcardlib.collect_vcard_names(vcard)
        # select the most relevant name
        selected_name = vcardlib.select_most_relevant_name(available_names)
        file_content = vcard.serialize()
        selected_name = selected_name.replace("/", "_")
        filename = os.path.join(out_dir, selected_name + ".vcf")
        with open(filename, 'w') as c_file:
            c_file.write(file_content)
        obj["new_filename"] = filename
    return changes



def run(folder_a, folder_b):
    print(folder_a)
    print(folder_b)
    c_a = get_contacts(folder_a)
    c_b = get_contacts(folder_b)

    all = {}
    for name in c_a:
        all[name] = c_a[name][:]
    for name in c_b:
        if name not in all:
            all[name] = c_b[name][:]
        else:
            all[name].extend(c_b[name][:])

    duplicates(all, "all")
    return merge_duplicates(all)


def merge_duplicates(all):
    merged = []
    for name in all:
        if len(all[name])>1:
            vcards = [v["vcard"] for v in all[name]]
            filenames = [os.path.join(v["folder"], v["file"]) for v in all[name]]
            attributes = vcardlib.collect_attributes(vcards)
            vcardlib.set_name(attributes)
            new = vcardlib.build_vcard(attributes)
            print(name, len(all[name]))
            print(new.prettyPrint())
            obj = {"vcard":new, "filenames":filenames}
            merged.append(obj)
    return merged

def duplicates(contacts, folder):
    print(f"Checking duplicates for {folder}")
    names = list(contacts.keys())
    duplicates = []
    for idx, name1 in enumerate(names[:-1]):
        for name2 in names[idx+1:]:
            if vcardlib.match_approx(name1, name2):
                duplicates.append((name1, name2))
    for name1, name2 in duplicates:
        contacts[name1].extend(contacts[name2])
        del contacts[name2]

def get_contacts(folder):
    contacts = {}
    for f in os.listdir(folder):
        if f.endswith(".vcf"):
            vcard = vobject.readOne(open(os.path.join(folder, f)).read())
            name = vcard.contents['fn'][0].value
            if name not in contacts:
                contacts[name] = []
            contacts[name].append({"vcard":vcard, "folder":folder, "file":f})
    return contacts




if __name__ == "__main__":
    main()
