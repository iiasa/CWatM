"""
CWatM version information: git hash, branch, commit date and dirty state of the code that runs

Found once when the model starts (no generated file, no extra commit), the first that works is used:

1. git clone, git on PATH: git log / rev-parse / describe / diff
2. git clone, git not on PATH: hash and branch from .git/HEAD, .git/refs/heads/<branch> or .git/packed-refs
   (no date, dirty: not checked) - reading these files here is an allowed exception to "all file I/O via
   data_handling"
3. zip / tar download from GitHub (no .git folder): the $Format:...$ placeholders below are filled by git archive
   (.gitattributes: cwatm/version.py export-subst)
4. nothing found: unknown

dirty: a tracked file of the model code (cwatm/ without *.md, run_cwatm.py) is changed against the commit;
dirty_id: first 6 characters of the sha1 of this change (two different dirty states have different ids)
"""

import hashlib
import os
import shutil
import subprocess

# filled by git archive (GitHub zip / tar download), in a clone they stay as they are
ARCHIVE_HASH = "$Format:%H$"
ARCHIVE_DATE = "$Format:%cI$"
ARCHIVE_REFS = "$Format:%D$"

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# model code for the dirty check (git pathspec)
MODELCODE = ["cwatm", "run_cwatm.py", ":(exclude)*.md"]

_info = None


def _git(*args):
    """output of one git command in the repository (stripped), None if git is missing or the command fails"""
    exe = shutil.which("git")
    if exe is None:
        return None
    try:
        r = subprocess.run([exe, *args], cwd=REPO, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def _gitdir():
    """.git folder of the repository (worktree: .git is a file 'gitdir: <path>'), None if there is none"""
    git = os.path.join(REPO, ".git")
    if os.path.isfile(git):
        with open(git, encoding="utf-8") as f:
            line = f.read().strip()
        if line.startswith("gitdir:"):
            git = os.path.join(REPO, line[7:].strip())
    return git if os.path.isdir(git) else None


def _info_dict(source, githash, short, branch, date, describe, dirty, dirty_id, changed=()):
    state = {True: "dirty", False: "verified", None: "not checked"}[dirty]
    if dirty_id:
        state += "." + dirty_id
    return {"source": source, "git_hash": githash, "git_short_hash": short, "git_branch": branch,
            "commit_date": date, "describe": describe, "dirty": dirty, "dirty_id": dirty_id, "state": state,
            "label": branch + " " + short + " " + state, "changed": list(changed)}


def _from_git():
    """version by git commands, None if git is not on PATH or the command fails"""
    out = _git("log", "-1", "--format=%H%n%h%n%cI")
    if out is None:
        return None
    githash, short, date = out.splitlines()
    branch = _git("rev-parse", "--abbrev-ref", "HEAD") or "HEAD"      # HEAD: detached (e.g. a tag checked out)
    describe = _git("describe", "--tags", "--always") or short
    names = _git("diff", "HEAD", "--name-only", "--", *MODELCODE)      # changed tracked files of the model code
    dirty = None if names is None else names != ""
    changed = names.splitlines() if names else []
    dirty_id = ""
    if dirty:
        diff = _git("diff", "HEAD", "--", *MODELCODE)
        if diff is not None:
            dirty_id = hashlib.sha1(diff.encode("utf-8", "replace")).hexdigest()[:6]
    return _info_dict("git", githash, short, branch, date, describe, dirty, dirty_id, changed)


def _from_files(gitdir):
    """hash and branch from the files of the .git folder (git not on PATH), None if not found"""
    with open(os.path.join(gitdir, "HEAD"), encoding="utf-8") as f:
        head = f.read().strip()
    if not head.startswith("ref:"):                                    # detached HEAD: the hash itself
        return _info_dict("git files", head, head[:7], "HEAD", "", head[:7], None, "")
    ref = head[4:].strip()                                             # refs/heads/develop
    # worktree: the refs are in the common .git folder
    common = gitdir
    if os.path.isfile(os.path.join(gitdir, "commondir")):
        with open(os.path.join(gitdir, "commondir"), encoding="utf-8") as f:
            common = os.path.join(gitdir, f.read().strip())
    githash = None
    if os.path.isfile(os.path.join(common, ref)):
        with open(os.path.join(common, ref), encoding="utf-8") as f:
            githash = f.read().strip()
    elif os.path.isfile(os.path.join(common, "packed-refs")):
        with open(os.path.join(common, "packed-refs"), encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) == 2 and parts[1] == ref:
                    githash = parts[0]
    if not githash:
        return None
    branch = ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else ref
    return _info_dict("git files", githash, githash[:7], branch, "", githash[:7], None, "")


def _from_archive():
    """version of a zip / tar download (placeholders filled by git archive), None in a clone"""
    if ARCHIVE_HASH.startswith("$Format"):
        return None
    refs = [r.strip() for r in ARCHIVE_REFS.split(",") if r.strip()]   # e.g. HEAD -> main, origin/main, tag: v1.9
    branch = next((r[len("HEAD -> "):] for r in refs if r.startswith("HEAD -> ")), "")
    if not branch:
        branch = next((r.split("/", 1)[-1] for r in refs if not r.startswith(("tag: ", "HEAD"))), "")
    tag = next((r[len("tag: "):] for r in refs if r.startswith("tag: ")), "")
    return _info_dict("archive", ARCHIVE_HASH, ARCHIVE_HASH[:7], branch or "unknown", ARCHIVE_DATE,
                      tag or ARCHIVE_HASH[:7], None, "")


def get_version_info():
    """version information as a dictionary - found once per process (calibration: many runs), then cached"""
    global _info
    if _info is None:
        info = None
        try:
            gitdir = _gitdir()
            if gitdir is not None:
                # only with a .git folder: git would otherwise find a repository above the CWatM folder
                info = _from_git() or _from_files(gitdir)
        except (OSError, ValueError):
            info = None
        _info = info or _from_archive() or _info_dict("unknown", "unknown", "unknown", "unknown", "", "unknown",
                                                     None, "")
    return _info


def version_attributes():
    """version attributes of the netCDF files (output maps, initial conditions, MODFLOW head)"""
    info = get_version_info()
    return {"git_branch": info["git_branch"], "git_commit": info["git_hash"], "git_describe": info["describe"],
            "git_dirty": info["state"]}


def print_version_info():
    """Print version information"""
    info = get_version_info()
    print("CWATM Version Information:")
    print(f"  Git Hash: {info['git_hash']}")
    print(f"  Short Hash: {info['git_short_hash']}")
    print(f"  Branch: {info['git_branch']}")
    print(f"  Describe: {info['describe']}")
    print(f"  Commit date: {info['commit_date']}")
    print(f"  Model code: {info['state']} (from: {info['source']})")
