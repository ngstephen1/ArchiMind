import pytest

from archimind.datasets.midi import (
    TEST_ROOMS,
    MidiIdentityError,
    archive_member_room,
    build_index,
    parse_furniture_id,
    parse_room_id,
)

H = "deaa4ac0-8d13-423f-930f-78fb25825e8d"
J1 = "69a2550c-ec04-44d9-a621-e601330a9cb6"
J2 = "b9237c75-6b5b-4c0f-a776-5ab036c5fb22"


def rooms(n):
    return [f"{H[:-4]}{i:04x}/Bedroom-{i}" for i in range(n)]


def test_parse_room_and_furniture_ids():
    assert parse_room_id(f"{H}/Bedroom-5088") == (H, "Bedroom-5088")
    assert parse_room_id(f"{H}/OtherRoom") == (H, "OtherRoom")
    f = parse_furniture_id(f"Cabinet_Shelf_Desk_{J2}_2")
    assert (f.category, f.jid, f.instance) == ("Cabinet_Shelf_Desk", J2, 2)
    assert parse_furniture_id(f"Bed_{J1}-(1)_7").jid == f"{J1}-(1)"


@pytest.mark.parametrize(
    "value", [f"{H}", f"{H}/../x", "x/Bedroom-1", f"{H}/Bed room-1", None]
)
def test_bad_room_ids(value):
    with pytest.raises(MidiIdentityError):
        parse_room_id(value)


@pytest.mark.parametrize(
    "value", [f"Sofa_{J1}", f"Unknown_{J1}_1", "Bed_not-a-jid_1", f"Bed_{J1}_x"]
)
def test_bad_furniture_ids(value):
    with pytest.raises(MidiIdentityError):
        parse_furniture_id(value)


def test_index_associates_by_position_and_marks_the_test_tail():
    ids = rooms(TEST_ROOMS + 2)
    furniture = [[f"Bed_{J1}_1"] for _ in ids]
    index = build_index(ids, furniture, test_room_ids=ids[-TEST_ROOMS:])
    assert index.splits[ids[0]] == "train" and index.splits[ids[1]] == "train"
    assert index.splits[ids[2]] == "test" and index.splits[ids[-1]] == "test"
    assert index.jid_categories == {J1: "Bed"}


def test_index_rejects_inconsistent_lists():
    ids = rooms(3)
    with pytest.raises(MidiIdentityError, match="length"):
        build_index(ids, [[]] * 2)
    with pytest.raises(MidiIdentityError, match="Duplicate MIDI room"):
        build_index([ids[0], ids[0]], [[], []])
    with pytest.raises(MidiIdentityError, match="last 1,000"):
        build_index(ids, [[]] * 3, test_room_ids=[ids[0]])
    with pytest.raises(MidiIdentityError, match="conflicting"):
        build_index(ids[:2], [[f"Bed_{J1}_1"], [f"Sofa_{J1}_1"]])
    with pytest.raises(MidiIdentityError, match="instance"):
        build_index(ids[:1], [[f"Bed_{J1}_1", f"Bed_{J1}_1"]])


def test_archive_member_room():
    base = f"3D-FRONT-TEST-SCENE/{H}"
    assert archive_member_room(f"{base}/Bedroom-1.glb") == f"{H}/Bedroom-1"
    assert archive_member_room(f"{base}/Bedroom-1_full.glb") == f"{H}/Bedroom-1"
    assert archive_member_room(f"{base}/Bedroom-1/Bed_{J1}_1.glb") == f"{H}/Bedroom-1"
    assert archive_member_room(f"{base}") is None
    assert archive_member_room("3D-FRONT-TEST-SCENE/../evil/x") is None


def test_join_report_uses_identity_and_flags_split_disagreement():
    from archimind.datasets.midi import join_report

    ids = rooms(TEST_ROOMS + 1)
    index = build_index(ids, [[f"Bed_{J1}_1"] for _ in ids])
    ssr = [
        (ids[0], "train", "canonical", (J1,)),  # midi train
        (ids[-1], "train", "reference_only", (J2,)),  # midi test -> disagreement
        (f"{H}/Bedroom-unknown", "test", "canonical", (J2,)),  # not in MIDI
    ]
    report = join_report(ssr, index)
    assert report["ssr_rows"] == 3 and report["joined_rows"] == 2
    assert report["split_pairs"] == {
        "ssr_train|midi_test": 1,
        "ssr_train|midi_train": 1,
    }
    assert report["split_disagreements"] == 1
    assert report["ssr_jids_with_midi_category"] == 1
    assert report["midi_categories_of_ssr_jids"] == {"Bed": 1}
