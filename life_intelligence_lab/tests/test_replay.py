import os

from life_intelligence_lab.downloader import download_amfi_nav
from life_intelligence_lab.scripts import parse_amfi_nav as parse_cli
from life_intelligence_lab.scripts import replay_amfi_nav as replay_cli


def _fake_fetch_from_fixture(fixture_text: str):
    from life_intelligence_lab.downloader import FetchResult

    body = fixture_text.encode("utf-8")

    def fetch_fn(url, timeout):
        return FetchResult(http_status=200, content_type="text/plain", body_bytes=body, error=None)

    return fetch_fn


# --- 15. Offline replay --------------------------------------------------------

def test_replay_cli_matches_original_parse_cli_hash(tmp_path, valid_fixture_text):
    snapshot_root = str(tmp_path / "snapshots")
    canonical_dir = str(tmp_path / "canonical" / "first_run")
    replay_dir = str(tmp_path / "canonical" / "replay_run")

    snapshot = download_amfi_nav(
        output_root=snapshot_root,
        fetch_fn=_fake_fetch_from_fixture(valid_fixture_text),
        snapshot_id="snap_replay_test",
    )
    snapshot_dir = os.path.join(snapshot_root, snapshot.snapshot_id)

    parse_exit = parse_cli.main(["--snapshot", snapshot_dir, "--out-dir", canonical_dir])
    assert parse_exit == 0

    replay_exit = replay_cli.main(
        ["--snapshot", snapshot_dir, "--out-dir", replay_dir, "--compare-to", canonical_dir]
    )
    assert replay_exit == 0  # CLI itself asserts MATCH internally; 0 means it matched


def test_replay_cli_fails_closed_on_missing_snapshot(tmp_path):
    exit_code = replay_cli.main(["--snapshot", str(tmp_path / "does_not_exist")])
    assert exit_code == 1  # no network attempted, no silent success


def test_replay_uses_no_network_module(tmp_path, valid_fixture_text):
    # Confirm replay_amfi_nav.py never imports urllib / the live fetch path.
    import inspect

    source = inspect.getsource(replay_cli)
    assert "urllib" not in source
    assert "default_http_fetch" not in source
