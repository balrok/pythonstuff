from Extension import Extension

class Generic(Extension):
    eregex = '.*'
    ename = "generic"
    # this will match for every regex, but we don't want that this will block others from being found
    # so give it the lowest priority
    ePriority = -1
