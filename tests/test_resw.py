from pathlib import Path
from tools.resw import read_resw, write_resw, materialize_zh


def test_resw_round_trip(tmp_path: Path):
    path = tmp_path / "Resources.resw"
    write_resw(path, {"A.Text": "Hello", "B.Content": "World"})
    assert read_resw(path) == {"A.Text": "Hello", "B.Content": "World"}


def test_materialize_zh_falls_back_and_reports():
    zh, fallback = materialize_zh({"A":"Hello","B":"World"}, {}, {"Hello":{"translation":"你好","state":"reviewed"}})
    assert zh == {"A":"你好","B":"World"}
    assert fallback == ["B"]


def test_materialize_zh_matches_memory_across_line_endings():
    source = 'REANIMAL has native HDR that is literally "HDR Den made".\rThere is no need to add RenoDX to this game.'
    reviewed = source.replace("\r", "\n")
    memory = {
        reviewed: {
            "translation": "REANIMAL 已原生支持 HDR。\n无需再为此游戏添加 RenoDX。",
            "state": "reviewed",
        }
    }

    zh, fallback = materialize_zh({"Data": source}, {}, memory)

    assert zh["Data"] == "REANIMAL 已原生支持 HDR。\n无需再为此游戏添加 RenoDX。"
    assert fallback == []
