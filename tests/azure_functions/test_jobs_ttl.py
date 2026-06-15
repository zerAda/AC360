"""Tests RGP-03 — prune_jobs_dir (purge âgée JOBS_BASE_DIR).

Couvre les cinq comportements verrouillés : suppression des anciens, conservation
des récents, base_dir absent toléré, échec par-entrée toléré, injection now/remover.
"""
import os

import jobs_ttl


def test_old_entries_deleted_fresh_kept(tmp_path):
    base = tmp_path / "jobs"
    base.mkdir()
    old = base / "old_job"
    fresh = base / "fresh_job"
    old.write_text("x")
    fresh.write_text("y")
    now = 1_000_000.0
    # old: mtime bien avant le cutoff ; fresh: après le cutoff.
    os.utime(old, (now - 100 * 86400, now - 100 * 86400))
    os.utime(fresh, (now - 1 * 86400, now - 1 * 86400))

    removed: list[str] = []
    deleted = jobs_ttl.prune_jobs_dir(
        str(base),
        max_age_seconds=30 * 86400,
        now=now,
        remover=removed.append,  # pas de suppression réelle
    )

    assert str(old) in deleted
    assert str(fresh) not in deleted
    assert removed == deleted  # le remover injecté a bien reçu uniquement l'ancien


def test_missing_base_dir_tolerated():
    deleted = jobs_ttl.prune_jobs_dir(
        os.path.join("does", "not", "exist"),
        max_age_seconds=30 * 86400,
        now=1_000_000.0,
        remover=lambda p: None,
    )
    assert deleted == []


def test_per_entry_oserror_does_not_abort(tmp_path):
    base = tmp_path / "jobs"
    base.mkdir()
    a = base / "a_old"
    b = base / "b_old"
    a.write_text("x")
    b.write_text("y")
    now = 1_000_000.0
    for p in (a, b):
        os.utime(p, (now - 100 * 86400, now - 100 * 86400))

    def flaky_remover(path: str) -> None:
        if path.endswith("a_old"):
            raise OSError("boom")  # une entrée échoue

    deleted = jobs_ttl.prune_jobs_dir(
        str(base), max_age_seconds=30 * 86400, now=now, remover=flaky_remover
    )
    # b est traité malgré l'échec sur a (best-effort, ne lève pas)
    assert str(b) in deleted
    assert str(a) not in deleted


def test_injected_now_governs_cutoff(tmp_path):
    base = tmp_path / "jobs"
    base.mkdir()
    item = base / "job"
    item.write_text("x")
    mtime = 500_000.0
    os.utime(item, (mtime, mtime))

    removed: list[str] = []
    # now juste après mtime -> sous la fenêtre -> conservé
    kept = jobs_ttl.prune_jobs_dir(
        str(base), max_age_seconds=10, now=mtime + 5, remover=removed.append
    )
    assert kept == []
    # now bien après -> au-delà de la fenêtre -> supprimé
    gone = jobs_ttl.prune_jobs_dir(
        str(base), max_age_seconds=10, now=mtime + 1000, remover=removed.append
    )
    assert str(item) in gone


def test_default_remover_actually_deletes(tmp_path):
    base = tmp_path / "jobs"
    base.mkdir()
    d = base / "old_dir"
    d.mkdir()
    (d / "f.txt").write_text("x")
    now = 1_000_000.0
    os.utime(d, (now - 100 * 86400, now - 100 * 86400))

    deleted = jobs_ttl.prune_jobs_dir(str(base), max_age_seconds=30 * 86400, now=now)
    assert str(d) in deleted
    assert not d.exists()  # le remover par défaut (rmtree) a bien supprimé le dossier
