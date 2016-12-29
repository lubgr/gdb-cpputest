
# gdb-cpputest: debugging shortcut for CppUTest

When unit tests of a project are written using [CppUTest](http://cpputest.github.io), you may want
to use [gdb](https://www.gnu.org/software/gdb) to examine a particular test failure. To to so, you
often

* set a breakpoint at the beginning of the failing unit test
* provide arguments for the executable to only run the failing test (speeds things up).

In gdb-cpputest.py, one gdb command `cppu` is provided that assists in accomplishing these two
things by searching for unit tests in the symbol table that match a given pattern.

Installation
------------
Download the python file and source it in your (possibly project-specific) `.gdbinit`, e.g.
```gdb
source /some/path/gdb-cpputest.py
```

Usage
-----
Compile your project with debugging flags (e.g. `-g -ggdb -O0`) and start gdb. You can then use the
`cppu` subcommands.
```gdb
(gdb) file path/to/testexecutable
(gdb) cppu name-of-failing-test
(gdb) run
```
If name-of-failing-test was unambiguous, this example will stop at the first line of this test.
Otherwise, a list of possible tests is printed out together with unique search strings to be used
for the `cppu` invocation. The following (sub-)commands are available:

* `cppu test [pattern]` sets the command-line arguments (-sg groupname -sn testname) but no break
  points
* `cppu break [pattern]` sets command-line arguments, deletes test break points and sets a new
  one for the given test
* `cppu clear` deletes all breakpoints at unit test functions
* `cppu [pattern]` an alias for `cppu break [pattern]`

The pattern will be used for a *case-insensitive* search. It can be enriched by ^ and $ to indicate
begin of the test group name and end of the test name itself. This circumvents situations in which
the name of a test case (or group) is contained in another.

Explanation
-----------
A unit test "Bar" in the test group "Foo" declared by the CppUTest macro `TEST(Foo, Bar) { ... }`
will result in function TEST_Foo_Bar_Test::testBody() { ... }. Thus, when using the above command,
all entries in the symbol table matching TEST_.*_Test::testBody() will be filtered by the given
pattern.
