#!/usr/bin/env python3
"""dirdiff - compare two directory trees.

Exit codes:
    0  identical
    1  differences found
    2  bad input
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass, asdict
from typing import Dict, Iterable, List

CHUNK = 1 << 20  # 1 MiB；大文件不一次性读进内存


@dataclass
class Entry:
    path: str          # 相对路径，统一用 /
    size: int
    digest: str = ""   # 惰性计算，大小相同时才用得上


@dataclass
class Diff:
    kind: str          # added / removed / changed
    path: str
    old_size: int = 0
    new_size: int = 0

    @property
    def delta(self) -> int:
        return self.new_size - self.old_size


def digest_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(CHUNK)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def scan(root: str, ignore: Iterable[str]) -> Dict[str, Entry]:
    """遍历目录，返回 {相对路径: Entry}。

    跳过符号链接，避免环路；ignore 按名字精确匹配，任意层级生效。
    """
    ignore_set = set(ignore)
    out: Dict[str, Entry] = {}
    root = os.path.abspath(root)
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [d for d in dirnames if d not in ignore_set]
        for name in filenames:
            if name in ignore_set:
                continue
            full = os.path.join(dirpath, name)
            if os.path.islink(full):
                continue
            try:
                st = os.stat(full)
            except OSError:
                continue
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            out[rel] = Entry(path=rel, size=st.st_size)
    return out


def _digest_of(entry: Entry, root: str) -> str:
    """惰性算摘要，结果缓存在 Entry 上。"""
    if not entry.digest:
        if not root:
            return ""
        full = os.path.join(root, entry.path.replace("/", os.sep))
        try:
            entry.digest = digest_file(full)
        except OSError:
            entry.digest = "<unreadable>"
    return entry.digest


def compare(a: Dict[str, Entry], b: Dict[str, Entry],
            root_a: str = "", root_b: str = "") -> List[Diff]:
    """比对两棵树。

    大小不同直接判 changed，只有大小相同才去算摘要 ——
    未变的文件只付一次 stat 的代价，这是常见情况。
    """
    diffs: List[Diff] = []
    for path in sorted(set(a) | set(b)):
        ea, eb = a.get(path), b.get(path)
        if ea is None:
            diffs.append(Diff("added", path, 0, eb.size))
        elif eb is None:
            diffs.append(Diff("removed", path, ea.size, 0))
        elif ea.size != eb.size:
            diffs.append(Diff("changed", path, ea.size, eb.size))
        elif _digest_of(ea, root_a) != _digest_of(eb, root_b):
            diffs.append(Diff("changed", path, ea.size, eb.size))
    return diffs


def human(n: int) -> str:
    if n < 1024:
        return "%d B" % n
    value = float(n)
    for unit in ("KB", "MB", "GB"):
        value /= 1024.0
        if value < 1024 or unit == "GB":
            return "%.1f %s" % (value, unit)
    return "%d B" % n


def render(diffs: List[Diff], changed_only: bool) -> str:
    mark = {"added": "+", "removed": "-", "changed": "~"}
    label = {"added": "added  ", "removed": "removed", "changed": "changed"}
    lines: List[str] = []
    for d in diffs:
        if changed_only and d.kind == "changed" and d.delta == 0:
            continue
        head = "%s %s %-40s" % (mark[d.kind], label[d.kind], d.path)
        if d.kind == "changed":
            lines.append("%s %10s -> %10s  (%+d)"
                         % (head, human(d.old_size), human(d.new_size), d.delta))
        else:
            lines.append("%s %10s" % (head, human(d.new_size or d.old_size)))
    return "\n".join(lines)


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="dirdiff", description="Compare two directory trees.")
    ap.add_argument("left")
    ap.add_argument("right")
    ap.add_argument("--ignore", action="append", default=[],
                    metavar="NAME", help="skip this name at any depth")
    ap.add_argument("--changed-only", action="store_true",
                    help="hide changed entries whose size did not move")
    ap.add_argument("--min-size", type=int, default=0,
                    help="ignore differences smaller than N bytes")
    ap.add_argument("--json", action="store_true", help="machine readable output")
    args = ap.parse_args(argv)

    for p in (args.left, args.right):
        if not os.path.isdir(p):
            print("dirdiff: not a directory: %s" % p, file=sys.stderr)
            return 2

    a = scan(args.left, args.ignore)
    b = scan(args.right, args.ignore)
    diffs = compare(a, b, args.left, args.right)

    if args.min_size:
        diffs = [d for d in diffs
                 if d.kind != "changed" or abs(d.delta) >= args.min_size]

    if args.json:
        print(json.dumps([asdict(d) for d in diffs], indent=2))
    elif diffs:
        print(render(diffs, args.changed_only))
        print()
        print("%d difference(s): %d added, %d removed, %d changed" % (
            len(diffs),
            sum(1 for d in diffs if d.kind == "added"),
            sum(1 for d in diffs if d.kind == "removed"),
            sum(1 for d in diffs if d.kind == "changed")))
    else:
        print("identical")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
