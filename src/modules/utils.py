import time
import shutil
import signal
import logging


def cooldown(func):
    """Wait between Jikan calls if necessary"""
    def wrapper(self, mal_id: int):
        wait = self.next_jikan_call - time.time()
        if wait > 0:
            time.sleep(wait)

        result = func(self, mal_id)
        if not result["request_cached"]:
            self.next_jikan_call = time.time() + 4

        return result

    return wrapper


def storage(func):
    """Holds a process if there is too less storage left"""
    def wrapper(*args, **kwargs):
        while shutil.disk_usage("/").free / 1000000 < 2.5:
            logging.warning("Disk is too full, processes have been halted for 3 hours")
            time.sleep(10800)

        return func(*args, **kwargs)
    return wrapper


class Timeout:
    """Kill a process if it exceeds the time limit"""
    def __init__(self, seconds=60, error_message="Operation aborted because of timeout"):
        self.seconds = seconds
        self.error_message = error_message

    def __enter__(self):
        """Setup timer"""
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Disable timer"""
        signal.alarm(0)

    def handle_timeout(self, signum, frame):
        """Raise error when time is up"""
        raise TimeoutError(self.error_message)
