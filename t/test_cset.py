# Prepare system for the test with:
#   cset shield -s -c 2-3 -k on
# The test assumes 4 CPUs.
#
# Feel free to improve the unit test.

from __future__ import unicode_literals
from __future__ import print_function
from cpuset import cset
from cpuset.util import CpusetException
import unittest

class TestCpuSetProperties(unittest.TestCase):

    def setUp(self):
        cset.rescan()
        self.test_set=cset.unique_set("user")

    def test_cpus(self):
        self.test_set.cpus = "2-3"
        self.assertEqual(self.test_set.cpus, "2-3")
        with self.assertRaises(AttributeError):
            del self.test_set.cpus

    def test_mems(self):
        self.test_set.mems = "0"
        self.assertEqual(self.test_set.mems, "0")
        with self.assertRaises(AttributeError):
            del self.test_set.mems

    def test_cpu_excl(self):
        self.test_set.cpu_exclusive = ""
        self.assertFalse(self.test_set.cpu_exclusive)
        with self.assertRaises(AttributeError):
            del self.test_set.cpu_exclusive

    def test_mem_excl(self):
        self.test_set.mem_exclusive = ""
        self.assertFalse(self.test_set.mem_exclusive)
        with self.assertRaises(AttributeError):
            del self.test_set.mem_exclusive

    def test_tasks(self):
        self.test_set.tasks = ""
        self.assertEqual(self.test_set.tasks, [])
        with self.assertRaises(AttributeError):
            del self.test_set.tasks

    def test_unused_code(self):
        # unused
        self.assertEqual(cset.lookup_task_from_proc(1), "/system")
        with self.assertRaises(CpusetException):
            cset.lookup_task_from_proc(99999999999)

        # unused + broken
        #print(cset.lookup_task_from_cpusets(1))
        with self.assertRaises(CpusetException):
            cset.lookup_task_from_cpusets(99999999999)

    def test_walk_set(self):
        # no special checking ATM
        self.assertEqual(type(cset.unique_set("root")), cset.CpuSet)
        root_set = cset.find_sets("/")
        for node in root_set:
            for x in cset.walk_set(node):
                self.assertEqual(type(x), cset.CpuSet)

    def test_cpuspec_check(self):
        # these overlap with cpuset_inverse tests bellow
        # remove them after the code duplicaton is eliminated
        self.assertEqual(cset.cpuspec_check("0-3"), None)
        self.assertEqual(cset.cpuspec_check("0-1,,3"), None)
        with self.assertRaises(CpusetException):
            print('check of 1-2-3:', cset.cpuspec_check("1-2-3"))
        with self.assertRaises(CpusetException):
            print('check of 1!2-3:', cset.cpuspec_check("1!2-3"))
        with self.assertRaises(CpusetException):
            # 999999 CPUs ought to be enough for anybody
            cset.cpuspec_check("999999", usemax=True)
        with self.assertRaises(CpusetException):
            print('check of -3:', cset.cpuspec_check("-3"))

    def test_cpuspec_to_hex(self):
        self.assertEqual(cset.cpuspec_to_hex("0-3"), "f")
        self.assertEqual(cset.cpuspec_to_hex("0-1,,3"), "b")
        with self.assertRaises(CpusetException):
            cset.cpuspec_to_hex("1-2-3")
        # ^^ remove them after the code duplicaton is eliminated

    def test_memspec_check(self):
        self.assertEqual(cset.memspec_check("0-3"), None)
        with self.assertRaises(CpusetException):
            cset.memspec_check("0!3")

    def test_cpuspec_inverse(self):
        self.assertEqual(cset.cpuspec_inverse("0,2"), "1,3")
        self.assertEqual(cset.cpuspec_inverse("0-1"), "2-3")
        self.assertEqual(cset.cpuspec_inverse("2-3"), "0-1")
        self.assertEqual(cset.cpuspec_inverse("0-1,3"), "2")
        self.assertEqual(cset.cpuspec_inverse("0,2-3"), "1")
        self.assertEqual(cset.cpuspec_inverse("0,,3-3"), "1-2")
        with self.assertRaises(CpusetException):
            cset.cpuspec_inverse("1-2-3")

    def test_calc_cpumask(self):
        self.assertEqual(cset.calc_cpumask(4), "1f")

if __name__ == '__main__':
    unittest.main()

