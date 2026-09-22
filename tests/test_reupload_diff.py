import copy
import re
from pathlib import Path

from fastapi.testclient import TestClient

from dlc.parser.dig_parser import parse_dig_file
from dlc.parser.netlist import build_netlist
from dlc.web import server

SAMPLE = Path("data/sample_circuits/30_bug_benchmark/bug3_wrong_cin/"
              "Wrong_cin.dig")


def _with_attrs(circuit, skip=()):
    return next(i for i, c in enumerate(circuit.components)
                if c.attributes and i not in skip)


def test_reupload_diff_counts_edits_and_suspect_hits():
    c1 = parse_dig_file(str(SAMPLE))
    nl1 = build_netlist(c1)
    idx = _with_attrs(c1)

    edited = copy.deepcopy(c1)
    edited.components[idx].attributes["Label"] = "edited"
    edited.wires.pop(0)
    keys, pins = server._component_marks(c1, nl1, [idx])
    d = server._reupload_diff(server._fingerprint(c1),
                              server._fingerprint(edited),
                              {"suspects": keys, "suspect_pins": pins})
    assert d["comps_changed"] == 1
    assert d["comps_added"] == 0 and d["comps_removed"] == 0
    assert d["wires_changed"] == 1
    assert d["had_suspects"] is True and d["touched_suspect"] is True

    elsewhere = copy.deepcopy(c1)
    other = _with_attrs(c1, skip={idx})
    elsewhere.components[other].attributes["Label"] = "elsewhere"
    d2 = server._reupload_diff(server._fingerprint(c1),
                               server._fingerprint(elsewhere),
                               {"suspects": keys, "suspect_pins": pins})
    assert d2["comps_changed"] == 1 and d2["touched_suspect"] is False

    d3 = server._reupload_diff(server._fingerprint(c1),
                               server._fingerprint(elsewhere), None)
    assert d3["had_suspects"] is False and "touched_suspect" not in d3


def test_upload_twice_reports_the_diff_and_test_rows():
    server._LAST_UPLOAD.clear()
    server._LAST_SUSPECTS.clear()
    client = TestClient(server.app)
    data = SAMPLE.read_bytes()

    r1 = client.post("/api/circuit",
                     files=[("files", (SAMPLE.name, data, "application/xml"))])
    f1 = r1.json()["files"][0]
    assert isinstance(f1["testcase_rows"], int) and f1["testcase_rows"] > 0
    assert f1["reupload"] is None

    # the student deletes one wire and uploads again
    edited = re.sub(rb"<wire>.*?</wire>", b"", data, count=1, flags=re.S)
    assert edited != data
    r2 = client.post("/api/circuit",
                     files=[("files", (SAMPLE.name, edited, "application/xml"))])
    f2 = r2.json()["files"][0]
    assert f2["reupload"]["wires_changed"] == 1
    assert f2["reupload"]["comps_changed"] == 0
    assert f2["reupload"]["had_suspects"] is False
