from Extension import Extension

class Test2(Extension):
    # just in case you don't know how to add multiple strings into a regex:
    eregex = '(^(http://)?(www\.)?amazon\.com(.*))|(amazon)'
    ename = "test2"
