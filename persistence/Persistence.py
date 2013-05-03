import cPickle as pickle
import os

'''
A class which extends from PersistableObject can persist all it's non-object properties

_notPersist = []
    * a list of all properties which shouldn't be persisted
_objCheck = True
    * when set to False it won't do any checks if a property is an object
      this might be done to be more performant
_cache_dir = 'cache'
    * a directory where this will get saved to
persist(self, key=''):
    * saves the __dict__ of the object (== it's properties)
    * Excluded are:
        properties starting with "_" for example _myVar
        properties which are inside the _notPersist list
        properties which are an object or are a list of objects
            - this one logs a warning
    * param key allows to specify an own unique key for persistance
      else it uses the classname

load(self, key='', min_modification_time=0)
    * loads the dictionary and applies all properties to the object
    * param key allows to specify an own unique key for persistance
      else it uses the classname
    * won't load when the pickle-file is older than min_modification_time


My thoughts why I started this:

There seems to be no simple persistence implementation:
    I want, that it automatically stores and loads class properties
    I want, that it doesn't throw exceptions and can be added/removed without
        much changes
    I didn't want a big dependency
    I didn't want big configuration

First idea was to directly use pickle:
    problem is, that I didn't want to persist the logger
    the only solution was to http://stackoverflow.com/questions/2345944/exclude-objects-field-from-pickling-in-python
    -> which was the basis for my Persistence library

To solve it without much effort I looked at ZODB:
    probleme here is, that it has many dependencies and seemingly the same problem, that one can't exclude attributes
    (at least not without giving them a _v_ prefix, which only makes sense together
'''

# helper from http://tech.blog.aknin.name/2011/12/11/walking-python-objects-recursively/
from collections import Mapping, Set, Sequence 
# dual python 2/3 compatability, inspired by the "six" library
string_types = (str, unicode) if str is bytes else (str, bytes)
iteritems = lambda mapping: getattr(mapping, 'iteritems', mapping.items)()
def objwalk(obj, path=(), memo=None):
    if memo is None:
        memo = set()
    iterator = None
    if isinstance(obj, Mapping):
        iterator = iteritems
    elif isinstance(obj, (Sequence, Set)) and not isinstance(obj, string_types):
        iterator = enumerate
    if iterator:
        if id(obj) not in memo:
            memo.add(id(obj))
            for path_component, value in iterator(obj):
                for result in objwalk(value, path + (path_component,), memo):
                    yield result
            memo.remove(id(obj))
    else:
        yield path, obj


class Persistence(object):
    _notPersist = ['logger']
    _objCheck = False
    _cache_dir = 'cache'

    def getPersistableDict(self):
        state = {}
        for i in self.__dict__:
            if i.startswith('_') or i in self._notPersist:
                continue
            val = self.__dict__[i]
            if self._objCheck:
                for path,iterval in objwalk(val):
                    if not isinstance(iterval, string_types) and isinstance(iterval, object):
                        self.logger.warning("Key '%s' is not persistable since it contains an object" %i)
                        self.logger.warning("Please add it to the _notPersist list")
                        continue
            state[i] = val
        return state

    def persist(self, key=''):
        self.logger.info("persisting...")
        if key is '':
            key = self.__class__.__name__
        state = self.getPersistableDict()
        try:
            return pickle.dump(state, self._getCacheFile(key), pickle.HIGHEST_PROTOCOL)
        except:
            self.logger.error("Pickle dumping error")
            return False

    def load(self, key='', min_modification_time = 0):
        self.logger.info("loading...")
        if key is '':
            key = self.__class__.__name__
        cFile = self._getCacheFile(key, False)
        if not cFile:
            return False
        if min_modification_time > 0:
            if min_modification_time > os.stat(cFile.name).st_mtime:
                self.logger("Didn't load %s because lower than min_modification_time" % (key))
                return False
        try:
            obj = pickle.load(cFile)
        except:
            self.logger.error("Pickle loading error")
            return False
        if obj:
            for i in obj:
                self.__dict__[i] = obj[i]
        return True

    # load/save helper
    def _getCacheFile(self, key, write=True):
        dirPath = self._cache_dir
        if not os.path.exists(dirPath):
            self.logger.info("creating cache directory")
            try:
                os.makedirs(dirPath)
            except:
                self.logger.error("Could not create directory for %s" % (dirPath))
                return False
        if not dirPath:
            return False
        filePath = os.path.join(dirPath, key+'.pickle')
        if write:
            return open(filePath, "w")
        else:
            if not os.path.exists(filePath):
                self.logger.warning("Could not find file %s" % (filePath))
                return False
            return open(filePath, "r")
