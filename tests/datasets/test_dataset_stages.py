import pytest

from archimind.datasets.stages import COMPLETE, run_stage, stage_key, sync_tree


def test_stage_runs_once_then_skips(tmp_path):
    calls = []

    def build(out):
        calls.append(out)
        (out / "result.jsonl").write_bytes(b'{"a":1}\n')

    first = run_stage(tmp_path, "probe", "1.0.0", {"source": "x"}, build)
    second = run_stage(tmp_path, "probe", "1.0.0", {"source": "x"}, build)
    assert not first.skipped and second.skipped and len(calls) == 1
    assert (first.directory / COMPLETE).is_file()


def test_changed_inputs_or_version_change_the_key():
    base = stage_key("probe", "1.0.0", {"source": "x"})
    assert base != stage_key("probe", "1.0.0", {"source": "y"})
    assert base != stage_key("probe", "1.0.1", {"source": "x"})
    assert base == stage_key("probe", "1.0.0", {"source": "x"})


def test_corrupted_output_is_rebuilt(tmp_path):
    def build(out):
        (out / "r.txt").write_text("ok")

    result = run_stage(tmp_path, "s", "1.0.0", {}, build)
    (result.directory / "r.txt").write_text("tampered")
    again = run_stage(tmp_path, "s", "1.0.0", {}, build)
    assert not again.skipped
    assert (again.directory / "r.txt").read_text() == "ok"


def test_failed_build_leaves_nothing(tmp_path):
    def build(out):
        (out / "half.txt").write_text("partial")
        raise RuntimeError("interrupted")

    with pytest.raises(RuntimeError):
        run_stage(tmp_path, "s", "1.0.0", {}, build)
    assert list((tmp_path / "s").iterdir()) == []


def test_sync_copies_changes_only_and_skips_unfinished(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    (src / "stage/key").mkdir(parents=True)
    (src / "stage/key/a.txt").write_text("1")
    (src / "stage/key.work").mkdir()
    (src / "stage/key.work/b.txt").write_text("unfinished")
    (src / "x.bin.partial").write_text("partial")

    first = sync_tree(src, dst)
    assert (first.copied, first.unchanged) == (1, 0)
    assert (dst / "stage/key/a.txt").read_text() == "1"
    assert not (dst / "stage/key.work").exists()
    assert not (dst / "x.bin.partial").exists()

    second = sync_tree(src, dst)
    assert (second.copied, second.unchanged) == (0, 1)

    (src / "stage/key/a.txt").write_text("2")
    third = sync_tree(src, dst)
    assert third.copied == 1 and (dst / "stage/key/a.txt").read_text() == "2"
    assert not list(dst.rglob("*.partial"))


def test_sync_from_missing_source_is_a_no_op(tmp_path):
    report = sync_tree(tmp_path / "missing", tmp_path / "dst")
    assert (report.copied, report.unchanged) == (0, 0)
