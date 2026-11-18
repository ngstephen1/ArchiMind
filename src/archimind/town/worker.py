import time

from .service import initialize, work_once

if __name__ == "__main__":
    initialize()
    while True:
        if not work_once():
            time.sleep(0.5)
