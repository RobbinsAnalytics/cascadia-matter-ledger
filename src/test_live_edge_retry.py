"""Prove Client._raw's new timeout behaviour with the network mocked out.

No request leaves the machine, no quota is spent, no repo file is written.
Each case asserts BEHAVIOUR -- what _raw returned or raised, and what it
counted -- not merely that the code path exists.
"""
import importlib.util
import io
import json
import pathlib
import sys
import urllib.error

SRC = (sys.argv[1] if len(sys.argv) > 1 else
       str(pathlib.Path(__file__).resolve().parent / "pull_live_edge.py"))
spec = importlib.util.spec_from_file_location("ple", SRC)
ple = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ple)

ple.time.sleep = lambda s: None          # no real waiting


class Resp:
    def __init__(self, payload):
        self._b = json.dumps(payload).encode()
    def read(self):
        return self._b
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def script(*outcomes):
    """urlopen that plays a fixed sequence of outcomes, recording calls."""
    calls = []
    seq = list(outcomes)
    def fake(req, timeout=None):
        calls.append(req.full_url)
        o = seq.pop(0)
        if isinstance(o, BaseException):
            raise o
        return Resp(o)
    return fake, calls


def http429():
    return urllib.error.HTTPError("u", 429, "Too Many", {"Retry-After": "1"},
                                  io.BytesIO(b""))


fails = 0
def case(name, fn):
    global fails
    try:
        fn()
        print("  PASS  %s" % name)
    except AssertionError as e:
        fails += 1
        print("  FAIL  %s  -- %s" % (name, e))


def t1():
    fake, calls = script(TimeoutError("read timed out"), {"ok": 1})
    ple.urllib.request.urlopen = fake
    c = ple.Client("t")
    out = c._raw("https://x/a")
    assert out == {"ok": 1}, out
    assert len(calls) == 2, calls
    assert c.timeout_retries == 1, c.timeout_retries

def t2():
    fake, calls = script(TimeoutError("one"), TimeoutError("two"))
    ple.urllib.request.urlopen = fake
    c = ple.Client("t")
    try:
        c._raw("https://x/a")
    except TimeoutError:
        pass
    else:
        raise AssertionError("second timeout was swallowed")
    assert len(calls) == 2, "retried more than once: %d calls" % len(calls)

def t3():
    fake, calls = script(urllib.error.URLError("connection reset"), {"ok": 2})
    ple.urllib.request.urlopen = fake
    c = ple.Client("t")
    assert c._raw("https://x/a") == {"ok": 2}
    assert c.timeout_retries == 1

def t4():
    # Regression: the existing 429 path must be untouched by the new branch.
    fake, calls = script(http429(), {"ok": 3})
    ple.urllib.request.urlopen = fake
    c = ple.Client("t")
    assert c._raw("https://x/a") == {"ok": 3}
    assert c.throttle_waits == 1 and c.timeout_retries == 0, \
        (c.throttle_waits, c.timeout_retries)

def t5():
    # A non-429 HTTP error must STILL raise immediately, not be retried as a
    # "network failure" -- HTTPError is a URLError subclass, so this is the
    # trap in the new except clause.
    err = urllib.error.HTTPError("u", 500, "Server Error", {}, io.BytesIO(b""))
    fake, calls = script(err, {"never": 1})
    ple.urllib.request.urlopen = fake
    c = ple.Client("t")
    try:
        c._raw("https://x/a")
    except urllib.error.HTTPError as e:
        assert e.code == 500
    else:
        raise AssertionError("HTTP 500 was retried instead of raised")
    assert len(calls) == 1, "HTTP 500 caused %d calls" % len(calls)
    assert c.timeout_retries == 0

def t6():
    # The usage() call inherits the retry.
    fake, calls = script(TimeoutError("slow"),
                         {"current_usage": [{"scope": "user", "rate": "125/day",
                                             "remaining": 125}]})
    ple.urllib.request.urlopen = fake
    c = ple.Client("t")
    u = c.usage()
    assert u["125/day"]["remaining"] == 125, u
    assert c.timeout_retries == 1

print("Client._raw, network mocked:")
case("a timeout is retried once and the retry's answer is returned", t1)
case("a second timeout is RAISED, not retried again", t2)
case("a connection-level URLError gets the same single retry", t3)
case("regression: the 429 path still works and is counted separately", t4)
case("an HTTP 500 is raised at once, NOT retried as a network failure", t5)
case("usage() inherits the retry", t6)
print()
print("ALL PASS" if not fails else "%d FAILED" % fails)
sys.exit(1 if fails else 0)
