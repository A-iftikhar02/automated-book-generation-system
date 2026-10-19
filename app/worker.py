"""Background worker: `python -m app.worker`."""

import logging
import signal
import threading

from .services.jobs import worker_loop


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    worker_loop(stop)


if __name__ == "__main__":
    main()
