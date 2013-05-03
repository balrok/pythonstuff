from Extension import Extension

# I want to show here, that you easily can add a extension to your existing classes without changing their code
class Test1(object):
    def somestuff(self):
        pass


# but it works only if you don't have too much public methods
class ExtensionTest1(Test1, Extension):
    eregex = '^(http://)?(www\.)?google\.com(.*)'
    ename = "test1"
    def somestuff(self):
        return Test1.somestuff(self)


# another possibility is to have multiple extensions in one file:
class AnotherExtensionTest1(Test1, Extension):
    eregex = '^(http://)?(www\.)?example\.com(.*)'
    ename = "another_test1"
    def somestuff(self):
        return Test1.somestuff(self)
