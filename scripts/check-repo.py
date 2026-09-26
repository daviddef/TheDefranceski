#!/usr/bin/env python3
"""Is the git object store actually intact? The check a green build cannot make.

On 27 September 2026 this archive reported itself perfectly healthy — clean
working tree, empty `git diff HEAD`, empty `git diff --cached`, the whole gate
ALL GREEN across twelve checks, 2,940 pages built — while **32 objects were
missing and 30 links were broken**. It was told to David and to four peer
sessions as "the one repo of nine with no damage". That was wrong, and it was
wrong because every test in the suite was the wrong KIND: they all read FILES.
Nothing read the object store.

The Booyzen session found the class first, and only by attempting a write:
`git commit` died with «invalid object … Error building trees» on a repository
whose status, diff and build were all clean.

THREE CHECKS, because one of them catches what the other two miss.

  1. Can git resolve HEAD at all. The Blazevic session's failure was a
     surviving ref naming an object that was gone — `fatal: bad object HEAD`.
     Neither of the other two probes catches that on its own.
  2. `fsck --connectivity-only`. The real one. Reads the history, not the
     index.
  3. `write-tree`. Cheap, and proves the INDEX is intact — but ONLY the index.
     Booyzen's 95 missing blobs mapped to only 84 paths in HEAD; the other
     eleven were superseded versions of scans, which write-tree cannot see and
     a build cannot see. For an archive whose product is its history, that
     difference is the whole point.

TWO WAYS TO MISREAD THE OUTPUT, both met in one afternoon:

  * `fsck` prints `dangling` lines and exits 0 after any reset, refetch, amend
    or rebase. They are normal debris. Treating non-empty output as failure
    reads a healthy repo as broken — this archive has four right now.
  * `git fsck | grep -E 'missing|broken'; echo $?` reports the exit code of
    GREP, which is 1 when it finds nothing. So it prints a failure code on
    every healthy repository. A check that alarms on the healthy case is not a
    check; it gets learned as noise and stops being read. The same trap made
    `git commit --dry-run` useless as a probe: it exits non-zero whenever
    nothing is staged, which is the normal state of a clean archive.

THE REPAIR, when this fails — the Booyzen session's, and better than re-cloning
because it is purely additive and keeps uncommitted work:

    git -c gc.auto=0 -c maintenance.auto=0 fetch --refetch origin main

It ignores what the local store claims to have, re-downloads, and writes a NEW
pack. It deletes nothing. It passed the permission classifiers of three
sessions where a plain `git reset` was refused as destructive.

**A FRESH CLONE IS OFTEN THE BETTER ANSWER, and the Falco session's reasoning
for why generalises.** A refetch repairs the object store and leaves
`node_modules` exactly as it was — so if `.bin` is also empty you still need an
install afterwards, and that install is the step that is dangerous when the
manifest is itself reverted: `npm ci` then faithfully installs the wrong pinned
kit, with no error at all. **A clone fixes both at once and CANNOT install from
a reverted lockfile, because a clone has no reverted lockfile in it.** The
trade is uncommitted work: a refetch keeps it, a clone does not. So — refetch
when you have local changes worth keeping and the object store is the only
fault; clone when `.bin` is empty too, or when you are not certain what else
came back stale.

**ITS PRECONDITION IS LOAD-BEARING AND THE COMMAND LOOKS ADDITIVE WITHOUT IT.**
It only works if the REMOTE holds the missing objects. A repository with
unpushed commits may be missing objects that exist nowhere else, and then
neither a refetch nor a re-clone recovers them. Chronicarum was 25 commits
ahead when this was written. **A repo that is ahead of its remote needs a
person, not a command.**
"""
import subprocess, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def git(*a):
    r = subprocess.run(["git", "-C", ROOT] + list(a), capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)

def main():
    fails = []

    # 1 — a ref can name an object that is gone.
    rc, out = git("rev-parse", "--verify", "HEAD")
    if rc != 0:
        fails.append("git cannot resolve HEAD: %s" % out.strip().splitlines()[0:1])
    head = out.strip()[:8] if rc == 0 else "?"

    # 2 — the history. `dangling` is debris; `missing` and `broken` are not.
    rc, out = git("fsck", "--connectivity-only")
    bad = [l for l in out.splitlines() if "missing" in l or "broken link" in l]
    dangling = len([l for l in out.splitlines() if l.startswith("dangling")])
    if rc != 0 or bad:
        fails.append("fsck: %d missing/broken (exit %d). First: %s"
                     % (len(bad), rc, bad[0] if bad else "-"))

    # 3 — the index.
    rc, out = git("write-tree")
    if rc != 0:
        fails.append("write-tree failed — the index names an object that is gone: %s"
                     % out.strip().splitlines()[-1:])

    # Context, not a failure: a repo ahead of its remote cannot be repaired by
    # a refetch, so say so where someone reading a failure will see it.
    _, ahead = git("rev-list", "--count", "origin/main..HEAD")
    ahead = ahead.strip() if ahead.strip().isdigit() else "?"

    if fails:
        print("check-repo: FAIL — the object store is damaged")
        for f in fails:
            print("  FAIL  %s" % f)
        print("  repair (keeps uncommitted work, object store only):")
        print("    git -c gc.auto=0 -c maintenance.auto=0 fetch --refetch origin main")
        print("  repair (also fixes a broken node_modules, discards uncommitted work):")
        print("    fresh clone — and it cannot install from a reverted lockfile")
        if ahead not in ("0", "?"):
            print("  ⚠ THIS REPO IS %s COMMIT(S) AHEAD OF origin/main. A refetch cannot" % ahead)
            print("    recover objects the remote never had. Get a person, not a command.")
        return 1

    print("check-repo: ok — HEAD %s resolves, history intact, index intact"
          "%s" % (head, (", %d dangling (normal debris)" % dangling) if dangling else ""))
    return 0

if __name__ == "__main__":
    sys.exit(main())
