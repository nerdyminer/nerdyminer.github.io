import hashlib
import json
import re
from pathlib import Path

FORBIDDEN_DIGESTS = frozenset(
    {
        "076794ec96f044e19b9f41f7bf2b5e4c09b550dfbde504811f073814e665644b",
        "7913bd6dbfac67c7cb421bfd378bbf4934db0c673c4c151ce2bf9531f49b7180",
        "e09e969031bd9a59661080578eee21bbdbdf5d377d7254d41898cdd007b3378a",
        "85ec17ad62ee5f0f99db293763ed947ccc40804c07142e33d8812661ca2c7701",
        "a5c9762437220ab4ca31bf75d46d4b934209408b2c04164a75e7753d5284bda8",
        "437a9d92f68d0421ccc0b5480f098f039487c3329b78789d4143a0324c5a2508",
        "a925617886e8799cc5be05aee17f9b70fa3e91370a471e06c21277c10804d0dc",
    }
)


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def test_public_runtime_contains_no_industrial_identifiers() -> None:
    root = Path(__file__).parents[1]
    public_files = [
        *root.joinpath("src").rglob("*.py"),
        *root.joinpath("conf").rglob("*.toml"),
        *root.joinpath("app-src", "src").rglob("*.ts"),
        *root.joinpath("app-src", "src").rglob("*.tsx"),
        *root.joinpath("scripts").rglob("*.py"),
        root / "README.md",
    ]
    payload = "\n".join(path.read_text(encoding="utf-8").lower() for path in public_files)
    words = re.findall(r"[a-z0-9]+", payload)
    candidates = {
        *words,
        *(f"{left} {right}" for left, right in zip(words, words[1:], strict=False)),
    }
    assert FORBIDDEN_DIGESTS.isdisjoint(digest(candidate) for candidate in candidates)


def test_public_frames_use_future_dates_and_generic_geometry() -> None:
    root = Path(__file__).parents[1]
    index = json.loads(
        (root / "app-src" / "public" / "frames" / "index.json").read_text(encoding="utf-8")
    )

    assert index["days"][0]["date"].startswith("2036-")
    assert 0 <= index["rotationDeg"] < 360
    assert 0 <= index["conveyor"]["bearingDeg"] < 360
    assert index["grid"]["verticalCellSizeM"] > 0
    assert [feeder["name"] for feeder in index["feeders"]] == [
        "A-1",
        "A-2",
        "A-3",
        "B-1",
        "B-2",
        "B-3",
    ]
    assert max(value for day in index["days"] for value in day["apexHeightM"]) < 35
