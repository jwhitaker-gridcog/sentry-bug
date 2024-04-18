import subprocess
import sentry_sdk
import multiprocessing
import argparse
import sys
import os

# set SENTRY_DSN in env


# worker: this worker is used in two demos: first by multiprocessing, second by subprocess.
def worker(baggage_and_tp):
    sentry_sdk.init(traces_sample_rate=1.0, environment="jarrad-local", debug=True)
    baggage, traceparent = baggage_and_tp
    try:
        with sentry_sdk.continue_trace(
            {"baggage": baggage, "sentry-trace": traceparent}, op="task", name="child"
        ) as worker_tx:
            # # workaround:
            # if worker_tx.parent_sampled:
            #     worker_tx.sampled = True
            #     worker_tx.init_span_recorder(1000)
            sentry_sdk.capture_message("hi")
    finally:
        sentry_sdk.Hub.current.flush()


# demo 1: worker is started with multiprocessing.Process(). baggage is passed with multiprocessing magic.
def main_multiprocessing():
    sentry_sdk.init(traces_sample_rate=1.0, environment="jarrad-local", debug=True)

    with sentry_sdk.start_transaction(op="task", name="parent") as tx:
        baggage, traceparent = sentry_sdk.get_baggage(), sentry_sdk.get_traceparent()

        proc = multiprocessing.Process(
            target=worker, name="worker", args=[(baggage, traceparent)]
        )
        proc.start()
        proc.join()


# helper for demo 2: pull baggage from env and pass to worker.
def worker_subprocess():
    baggage, traceparent = (
        os.environ["SENTRY_BAGGAGE"],
        os.environ["SENTRY_TRACEPARENT"],
    )
    worker((baggage, traceparent))


# demo 2: worker is started with subprocess. baggage is passed with env vars.
def main_subprocess():
    sentry_sdk.init(traces_sample_rate=1.0, environment="jarrad-local", debug=True)

    with sentry_sdk.start_transaction(op="task", name="parent") as tx:
        baggage, traceparent = sentry_sdk.get_baggage(), sentry_sdk.get_traceparent()

        subprocess.run(
            [sys.executable, sys.argv[0], "worker_subp"],
            check=True,
            env={
                "SENTRY_BAGGAGE": baggage or "",
                "SENTRY_TRACEPARENT": traceparent or "",
            },
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=["main_mp", "main_subp", "worker_subp"],
    )
    args = parser.parse_args()
    match args.command:
        # demo 1
        case "main_mp":
            main_multiprocessing()
        # demo 2
        case "main_subp":
            main_subprocess()
        # helper for demo 2, you shouldn't need to call this yourself
        case "worker_subp":
            worker_subprocess()
        case other:
            raise Exception(f"unreachable: {other}")
