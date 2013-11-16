
import inspect
import os
from threading import Thread
import time
import unittest

from pdagent.filelock import FileLock, LockTimeoutException


TEST_HELPER_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "filelock-test-helper.py")

TEST_LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_filelock_lock.txt")


def run_helper(test_name=None):
    if not test_name:
        test_name = inspect.stack()[1][3]  # default to the same name as the calling test method
    e = os.system("python %s %s" % (TEST_HELPER_PY, test_name))
    exit_code, signal = e / 256, e % 256
    return exit_code, signal


class FileLockTest(unittest.TestCase):

    def setUp(self):
        if os.path.exists(TEST_LOCK_FILE):
            os.unlink(TEST_LOCK_FILE)
        #
        self.lock = FileLock(TEST_LOCK_FILE)
        # Ensure that some other process is not holding the lock
        self.lock.acquire()
        self.lock.release()

    def test_spawn_ok(self):
        # this test just to check if we're spawning the helper correctly
        e = run_helper()
        self.assertEqual(e, (10, 0))

    def test_simple_lock_internal(self):
        self.assertFalse(os.path.exists(TEST_LOCK_FILE))
        self.lock.acquire()
        self.assertTrue(os.path.exists(TEST_LOCK_FILE))
        self.lock.release()
        self.assertFalse(os.path.exists(TEST_LOCK_FILE))

    def test_simple_lock(self):
        self.assertEqual(run_helper(), (20, 0))
        self.assertFalse(os.path.exists(TEST_LOCK_FILE))

    def test_simple_lock_file_exists(self):
        open(TEST_LOCK_FILE, "w").write("-1\n")
        self.assertEqual(run_helper("test_simple_lock"), (20, 0))
        self.assertFalse(os.path.exists(TEST_LOCK_FILE))

    def test_lock_timeout(self):
        self.lock.acquire()
        self.assertEqual(run_helper(), (30, 0))
        self.lock.release()

    def test_lock_timeout_other_way_around(self):
        trace = []
        self.lock.timeout = 1
        #
        def f():
            try:
                trace.append("A")
                time.sleep(2) # Pause to allow helper acquire the lock
                trace.append("B")
                self.lock.acquire()
                trace.append("C")
                self.lock.release()
                trace.append("D")
            except LockTimeoutException:
                trace.append("T")
            except:
                trace.append("E")
        #
        t = Thread(target=f)
        t.start()
        time.sleep(1)
        self.assertEqual(trace, ["A"])
        #
        self.assertEqual(run_helper(), (35, 0))
        #
        t.join()
        self.assertEqual(trace, ["A", "B", "T"])

    def test_exit_without_release(self):
        self.assertEqual(run_helper(), (40, 0))
        self.lock.acquire()
        self.lock.release()

    def test_kill_releases_lock(self):
        self.assertEqual(run_helper(), (0, 9))
        self.assertTrue(os.path.exists(TEST_LOCK_FILE))
        self.lock.acquire()
        self.lock.release()
        self.assertFalse(os.path.exists(TEST_LOCK_FILE))


if __name__ == '__main__':
    unittest.main()