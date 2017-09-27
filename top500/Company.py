#!/usr/bin/env python3
# -*- coding: utf-8 -*-


class Company:
    def __init__(self, name, detail_id, position):
        self.name = name
        self.detail_id = detail_id
        self.position = position
        self.details = {}

    def set_details(self, details):
        self.details = details


def test():
    c1 = Company("Test", 22444, 1)
    c2 = Company("Test2", 22445, 2)
    #def __init__(self, name, detail_id, position):
    print(jsonpickle.encode([c1,c2]))



if __name__ == "__main__":
    test()
