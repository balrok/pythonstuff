#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import requests_cache
import tqdm
import jsonpickle
from lxml.html import fromstring
from Company import Company
requests_cache.install_cache('top500')
r = requests.session()

# for debugging
# import logging
# import http.client as http_client
# http_client.HTTPConnection.debuglevel = 1
# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True


def main():
    try:
        companies = json_load()
    except:
        companies = url_load()
        json_dump(companies)
    print_companies(companies)

def url_load():
    url = "http://top500.welt.de/list/2014/U/?i=1000&e=1000&p=1"
    text = r.get(url).text
    tree = fromstring(text)
    #tree.make_links_absolute(url)
    pos = 0
    companies = []
    for el in tqdm.tqdm(tree.find_class("grid_6")):
        a = el.find(".//a")
        if a is None:
            continue
        pos += 1
        href = a.attrib["href"]
        detail_id = [int(s) for s in href.split("/") if s.isdigit()][-1]
        name = str(a.text_content())
        comp = Company(name, detail_id, pos)
        details = get_details(detail_id)
        comp.set_details(details)
        companies.append(comp)
    return companies


def json_load():
    with open('top500.json', 'r') as content_file:
        content = content_file.read()
        return jsonpickle.decode(content)

def json_dump(companies):
    with open('top500.json', 'w') as content_file:
        content = jsonpickle.encode(companies)
        content_file.write(content)


def get_details(detail_id):
    details = {}
    url = "http://top500.welt.de/detail/%d/" % (detail_id)
    text = r.get(url).text
    tree = fromstring(text)
    key = None
    value = None
    for el in tree.find_class("tablecontent"):
        strong = el.find("strong")
        if key is None:
            if strong is not None:
                key = str(strong.text_content())
        else:
            if strong is None:
                value = str(el.text_content())
                if value.isdigit():
                    value = int(value)
            details[key] = value
            key = None
            value = None
    return details


def print_companies(companies):
    import pprint
    for c in companies:
        print(c.position, c.name, c.detail_id)
        pprint.pprint(c.details)


if __name__ == "__main__":
    main()
