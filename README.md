# dirdiff

Compare two directory trees and report what actually changed — files added,
removed, or modified, with byte-level size deltas.

Zero dependencies, single file, works on Windows / Linux / macOS.

## Why

`diff -r` prints a wall of text. `dirdiff` prints one line per difference and
returns an exit code you can branch on in scripts.

## Install

```bash
git clone https://github.com/SusieCommons/dirdiff.git
cd dirdiff
python dirdiff.py --help
```

Or grab just the script:

```bash
curl -O https://raw.githubusercontent.com/SusieCommons/dirdiff/main/dirdiff.py
```

## Usage

```bash
# basic
python dirdiff.py ./backup-a ./backup-b

# hide entries whose size did not move
python dirdiff.py ./a ./b --changed-only

# ignore differences smaller than 1 KiB
python dirdiff.py ./a ./b --min-size 1024

# skip noise directories at any depth
python dirdiff.py ./a ./b --ignore .git --ignore node_modules --ignore __pycache__

# machine readable
python dirdiff.py ./a ./b --json
```

## Exit codes

| code | meaning |
| --- | --- |
| 0 | trees identical |
| 1 | differences found |
| 2 | bad arguments or unreadable path |

## Output

```
+ added   new.txt                                      2.4 KB
- removed gone.txt                                      100 B
- removed node_modules/x.js                               3 B
~ changed src/main.py                                     9 B ->        9 B  (+0)

4 difference(s): 1 added, 2 removed, 1 changed
```

`+` added, `-` removed, `~` modified. Modified lines show before -> after and
the delta.

## How it compares

Files are matched by relative path. A file counts as unchanged when its size
and SHA-256 digest both match. The digest is only computed when sizes are
equal, so the common case — a tree full of untouched files — costs one `stat`
per file and no reads.

## Tests

```bash
python -m unittest discover -s tests -v
```

Nine tests covering scan, compare, and CLI exit codes.

## License

MIT
