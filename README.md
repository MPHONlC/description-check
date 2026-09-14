# Description Check

Compares description content across BBCode (any forum using BBCode), GitHub Flavored Markdown, and Bethesda (CommonMark), ignoring each platform's own formatting AND each platform's own section ordering - a sentence appearing earlier on one platform than another is not treated as a mismatch. Reports a sentence-match count for every pair (BBCode vs GitHub, GitHub vs Bethesda, BBCode vs Bethesda), with the actual differing sentences listed - it never fails the run, since some wording variation between platforms is normal for a description page (unlike a changelog, which is expected to match exactly - see [changelog-check](https://github.com/MPHONlC/changelog-check) for that).

It knows the real structural differences between the three platforms out of the box:
- GitHub-only decoration (badge images, an `<div align="center">` header block, `> [!NOTE]`/`> [!WARNING]`/etc. admonition markers, markdown tables) is stripped/unwrapped before comparing, not treated as content.
- `<kbd>`, `<sub>`, `**bold**`, backtick code spans, and markdown/BBCode links are all normalized to plain text on the relevant platform.

## Handling content that's intentionally platform-only

Some content is deliberately only on one platform - a donation link, a legal disclaimer, anything you never meant to duplicate everywhere. List those as regex patterns (one per line, case-insensitive, `#` for comments) in a file and point `ignore_patterns_file` at it; any line in any description file matching one of those patterns is dropped before comparing, so it's never flagged as a false mismatch.

```
# .github/description-ignore.txt
This add-on is not created by, affiliated with, or sponsored by ZeniMax Media Inc
If you like the addon and are considering donating
buymeacoffee
```

## Usage

```yaml
name: Description Content Check

on:
  push:
    branches: [main]
    paths:
      - 'README_BBCODE.txt'
      - 'README_COMMONMARK.txt'
      - 'README.md'
      - '.github/description-ignore.txt'
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: MPHONlC/description-check@Version-0.0.2
```

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `bbcode_file` | No | *(auto-detect)* | Path to the BBCode-forum description file. Leave blank to auto-detect `README_BBCODE.txt`, then `README_ESOUI.txt` (any case). |
| `github_file` | No | `README.md` | Path to the GitHub Flavored Markdown description file (usually the repo README) - this is GitHub's own required filename, so it is not auto-detected. |
| `bethesda_file` | No | *(auto-detect)* | Path to the Bethesda (CommonMark) description file. Leave blank to auto-detect `README_COMMONMARK.txt`, then `README_PLAINMARKDOWN.txt`, then `README_BETHESDA.txt` (any case). |
| `ignore_patterns_file` | No | `.github/description-ignore.txt` | Regex patterns (one per line) to drop from all three files before comparing. Missing file = no exclusions. |
| `manifest_file` | No | `''` | Optional `.addon` manifest. If set, fails the run when a description file mentions an AddOnVersion number that doesn't match the manifest's real `## AddOnVersion:`. Leave blank to skip. |

## AddOnVersion staleness check

If `manifest_file` is set, every description file is scanned line by line for the word "AddOnVersion" (case-insensitive). Any line containing it that also has a number not matching the manifest's real `## AddOnVersion:` value fails the run - catches a hardcoded build number in your README going stale after a real update. Unlike the similarity comparison above, this check does fail on a mismatch.

<details>
<summary>Example step summary output</summary>

````
## Description content comparison

Ignoring 3 known platform-specific pattern(s) from `.github/description-ignore.txt` (e.g. donation links, legal boilerplate that isn't meant to appear on every platform).

Compared sentence-by-sentence, ignoring each platform's own ordering and formatting - a section appearing earlier on one platform than another is not itself a mismatch.

**BBCode vs GitHub**: 11/12 sentences in BBCode also appear in GitHub.

<details><summary>Sentences that differ (BBCode vs GitHub)</summary>

Only in BBCode:
- Auto Lua Memory Cleaner A lightweight, event-driven background memory cleaner.
Only in GitHub:
- Auto Lua Memory Cleaner is a lightweight, event-driven background memory cleaner.

</details>
````

</details>

## License

MIT - see [LICENSE](LICENSE).
