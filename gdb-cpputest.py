
import re

class Test(object):
    def __init__(self, definition):
        self.definition = definition

        self.setGroupName()
        self.setTestName()

    def setTestName(self):
        self.name = ''
        lookupStr = 'TEST_' + self.group

        first = self.definition.rfind(lookupStr) + len(lookupStr) + 1
        second = self.definition.find('::') - len('_Test')

        self.name = self.definition[first:second]

        if not self.name:
            self.name = '(not found)'

    def setGroupName(self):
        identStr = self.definition.replace('void TEST_', '', 1)
        identStr = identStr.replace('_Test::testBody();', '', 1)

        lookupBase = 'TEST_GROUP_CppUTestGroup'
        groupName, self.group = '', ''

        for part in identStr.split('_'):
            groupName += part
            lookupStr = lookupBase + groupName
            try:
                gdb.lookup_type(lookupStr)
                self.group = groupName
                return
            except:
                groupName += '_'

        self.group = '(not found)'

    def __str__(self):
        return self.group + ' ' + self.name

    def __repr__(self):
        return self.__str__()

    def getUniqueString(self):
        return self.group + '_' + self.name

    def getBreakPointIdentifier(self):
        return 'TEST_' + self.group + '_' + self.name + '_Test::testBody()'

    def getArgsString(self):
        return '-sg ' + self.group + ' -sn ' + self.name

class TestSelector(object):
    def __init__(self, searchStr):
        self.queryStr = searchStr
        self.caseSetting = 'auto'

    def getTests(self):
        matches = self.getMatches()
        localTests = []

        for match in matches:
            localTests.append(Test(match))

        return localTests

    def getMatches(self):
        fullQuery = 'TEST_'

        if self.queryStr.startswith('^'):
            self.queryStr = self.queryStr[1:]
        else:
            fullQuery += '.*'

        if self.queryStr.endswith('$'):
            fullQuery += self.queryStr[0:-1]
        else:
            fullQuery += self.queryStr + '.*'

        fullQuery += '_Test::testBody'

        self.storeCaseSensitivity()
        self.setCaseInsensitive()

        result = gdb.execute('info functions ' + fullQuery, False, True)

        self.restoreCaseSensitivity()

        return self.filterQuery(result)

    def storeCaseSensitivity(self):
        settingStr = gdb.parameter('case-sensitive')

        if settingStr.find('\"on\".') != -1:
            self.caseSetting = 'on'
        elif settingStr.find('\"off\".') != -1:
            self.caseSetting = 'off'
        else:
            self.caseSetting = 'auto'

    def setCaseInsensitive(self):
        gdb.execute('set case-sensitive off', False, True)

    def restoreCaseSensitivity(self):
        gdb.execute('set case-sensitive ' + self.caseSetting, False, True)

    def filterQuery(self, result):
        pattern = re.compile('void *TEST_.*_Test::testBody\(\);')
        filtered = []

        for line in re.findall(pattern, result):
            filtered.append(line)

        return filtered


class Color(object):
    colorizeOutput = True

    def white(self):
        return self.get('\033[0m')

    def green(self):
        return self.get('\033[32m')

    def yellow(self):
        return self.get('\033[33m')

    def get(self, colorStr):
        if self.colorizeOutput:
            return colorStr
        else:
            return ''

class Outputter(object):
    def __init__(self, tests):
        self.tests = tests
        self.col = Color()
        nameLength = len(self.getLongestTestName())
        self.testFormat = "%-" + str(nameLength) + "s"

    def printTests(self):
        try:
            self.printTestsOrBeInterrupted()
        except KeyboardInterrupt:
            pass

    def printTestsOrBeInterrupted(self):
        currentGroup = ''
        doPrintIdentifier = self.needsIdentifier()

        for test in self.tests:
            if currentGroup != test.group:
                currentGroup = test.group
                groupStr = self.col.green() + currentGroup + self.col.white()
                print(groupStr)

            testName = self.col.yellow() + self.testFormat % test.name + self.col.white()

            output = '  ' + testName
            if doPrintIdentifier:
                uniqueStr = test.getUniqueString()
                output += '  ' + uniqueStr

            print(output)

    def getLongestTestName(self):
        longest = ''
        for test in self.tests:
            if len(test.name) > len(longest):
                longest = test.name
        return longest

    def needsIdentifier(self):
        names = []
        for test in self.tests:
            names.append(test.name)

        for name in names:
            for otherName in names:
                if otherName == name:
                    continue
                elif name.find(otherName) != -1:
                    return True

        return False

def getTestsFromArg(gdbArg):
    argList = gdb.string_to_argv(gdbArg)
    queryStr = '' if len(argList) == 0 else argList[0]
    selector = TestSelector(queryStr)
    return selector.getTests()

def select(test):
    argString = test.getArgsString()
    argCmd = 'set args ' + argString

    gdb.execute(argCmd, False, True)

    print('Args have been set to ' + argString)

class CppUTest(gdb.Command):
    """Handle CppUTest tests quickly by searching the symbol table
    
A given pattern argument will be searched for in the symbol table, both test
groups and test cases are considered. Multiple matches are printed out together
with a unique search string to be used for an exact lookup. Search string can
start with ^ to indicate the test group and/or end with $ to mark the end of the
test name, which makes the query more precise. Passing this pattern to the
'cppu' command is a shortcut for using 'cppu break [pattern]'"""

    def __init__(self):
        gdb.Command.__init__(self, "cppu", gdb.COMMAND_USER, gdb.COMPLETE_NONE, True)

    def invoke(self, arg, from_tty):
        breakCmd = CppUTestBreak()
        breakCmd.invoke(arg, from_tty)

class CppUTestSelect(gdb.Command):
    """Select a test by command line arguments (-sg and -sn) for the executable"""

    def __init__(self):
        gdb.Command.__init__(self, "cppu test", gdb.COMMAND_USER, gdb.COMPLETE_COMMAND)

    def invoke(self, arg, from_tty):
        tests = getTestsFromArg(arg)

        if len(tests) == 0:
            print("No tests found")
        elif len(tests) > 1:
            Outputter(tests).printTests()
        else:
            select(tests[0])

class CppUTestBreak(gdb.Command):
    """Select a test (see cppu test) and set a breakpoint to its beginning"""
    def __init__(self):
        gdb.Command.__init__(self, "cppu break", gdb.COMMAND_USER, gdb.COMPLETE_NONE)

    def invoke(self, arg, from_tty):
        tests = getTestsFromArg(arg)

        if len(tests) == 0:
            print("No tests found")
        elif len(tests) > 1:
            Outputter(tests).printTests()
        else:
            test = tests[0]
            select(test)

            clearCmd = CppUTestClear()
            clearCmd.invoke(arg, from_tty)

            bpStr = test.getBreakPointIdentifier()
            gdb.Breakpoint(bpStr)

class CppUTestClear(gdb.Command):
    """Clear breakpoints at the beginning of unit tests"""
    def __init__(self):
        gdb.Command.__init__(self, "cppu clear", gdb.COMMAND_USER, gdb.COMPLETE_NONE)

    def invoke(self, arg, from_tty):
        breakpoints = gdb.execute('info breakpoints', False, True)

        for line in breakpoints.split('\n'):
            pattern = re.compile('^ *([0-9]+).*TEST_(.*)_Test::testBody\(\)')
            match = pattern.search(line)

            if match:
                gdb.execute('delete breakpoint %s' % match.group(1))
                print('deleted breakpoint %s' % match.group(2))

CppUTest()
CppUTestSelect()
CppUTestBreak()
CppUTestClear()
