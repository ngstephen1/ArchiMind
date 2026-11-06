import pytest

from archimind.datasets.canonical import (
    CanonicalError,
    canonical_bytes,
    digest,
    iter_jsonl,
    strict_loads,
    write_jsonl,
)


def test_key_order_and_float_noise_do_not_change_digest():
    a = {"b": 1, "a": [0.1 + 0.2, -0.0]}
    b = {"a": [0.3, 0.0], "b": 1}
    assert canonical_bytes(a) == canonical_bytes(b)
    assert digest(a) == digest(b)


def test_tuples_and_lists_are_equivalent():
    assert canonical_bytes({"v": (1, 2)}) == canonical_bytes({"v": [1, 2]})


@pytest.mark.parametrize("value", [float("nan"), float("inf"), {1: "x"}, object()])
def test_non_canonical_values_are_rejected(value):
    with pytest.raises(CanonicalError):
        canonical_bytes({"v": value})


@pytest.mark.parametrize(
    "text", ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', "{", b"\xff"]
)
def test_strict_loads_rejects_ambiguous_json(text):
    with pytest.raises(CanonicalError):
        strict_loads(text)


def test_strict_loads_size_limit():
    with pytest.raises(CanonicalError):
        strict_loads('{"a":"' + "x" * 100 + '"}', max_bytes=50)


def test_jsonl_round_trip_is_lf_only_and_deterministic(tmp_path):
    records = [{"id": 2, "x": 1.5}, {"id": 1}]
    sha1, n = write_jsonl(tmp_path / "a.jsonl", records)
    sha2, _ = write_jsonl(tmp_path / "b.jsonl", records)
    assert n == 2 and sha1 == sha2
    data = (tmp_path / "a.jsonl").read_bytes()
    assert b"\r" not in data and data.endswith(b"\n")
    assert list(iter_jsonl(tmp_path / "a.jsonl")) == records


def test_jsonl_rejects_crlf_long_lines_and_too_many_records(tmp_path):
    crlf = tmp_path / "crlf.jsonl"
    crlf.write_bytes(b'{"a":1}\r\n')
    with pytest.raises(CanonicalError):
        list(iter_jsonl(crlf))
    long = tmp_path / "long.jsonl"
    long.write_bytes(b'{"a":"' + b"x" * 200 + b'"}\n')
    with pytest.raises(CanonicalError):
        list(iter_jsonl(long, max_line_bytes=64))
    many = tmp_path / "many.jsonl"
    many.write_bytes(b"{}\n" * 5)
    with pytest.raises(CanonicalError):
        list(iter_jsonl(many, max_records=4))
