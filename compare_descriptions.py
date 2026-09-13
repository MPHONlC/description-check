import os
import re
import sys
import argparse
import difflib


PLATFORM_ALIASES = {
    'bbcode': ['BBCODE', 'ESOUI'],
    'commonmark': ['COMMONMARK', 'PLAINMARKDOWN', 'BETHESDA'],
}


def resolve_platform_file(explicit, prefix, kind):
    if explicit:
        return explicit
    aliases = PLATFORM_ALIASES[kind]
    try:
        entries = os.listdir('.')
    except OSError:
        entries = []
    for alias in aliases:
        pattern = re.compile(r'^' + re.escape(prefix) + r'_' + re.escape(alias) + r'\.txt$', re.IGNORECASE)
        for entry in entries:
            if pattern.match(entry):
                return entry
    return f'{prefix}_{aliases[0]}.txt'


def read(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return None


def load_ignore_patterns(path):
    text = read(path)
    if text is None:
        return []
    patterns = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        patterns.append(line)
    return patterns


def strip_ignored_lines(text, patterns):
    if not patterns:
        return text
    compiled = [re.compile(p, re.IGNORECASE) for p in patterns]
    kept = [line for line in text.splitlines() if not any(p.search(line) for p in compiled)]
    return '\n'.join(kept)


def flatten_bbcode(text, ignore_patterns):
    t = strip_ignored_lines(text, ignore_patterns)
    t = re.sub(r'\[url="[^"]*"\]', '', t)
    t = re.sub(r'\[/url\]', '', t)
    t = re.sub(r'\[\*\]', '', t)
    t = re.sub(r'\[/?[A-Za-z]+(=[^\]]*)?\]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def flatten_plain_md(text, ignore_patterns):
    t = strip_ignored_lines(text, ignore_patterns)
    t = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'\1', t)
    t = re.sub(r'`([^`]+)`', r'\1', t)
    t = re.sub(r'^#{1,6}\s*', '', t, flags=re.M)
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)
    t = re.sub(r'^\s*[-*]\s+', '', t, flags=re.M)
    t = re.sub(r'(?<!\w)\*([^*\n]+)\*(?!\w)', r'\1', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def flatten_github_md(text, ignore_patterns):
    t = strip_ignored_lines(text, ignore_patterns)
    t = re.sub(r'<div[^>]*>.*?</div>', '', t, flags=re.S)
    t = re.sub(r'</?details>', '', t)
    t = re.sub(r'<summary>.*?</summary>', '', t, flags=re.S)
    t = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', t)
    lines = []
    for line in t.splitlines():
        if re.match(r'^\s*>\s*\[!(NOTE|WARNING|IMPORTANT|TIP|CAUTION)\]\s*$', line, re.IGNORECASE):
            continue
        m = re.match(r'^\s*>\s?(.*)$', line)
        lines.append(m.group(1) if m else line)
    t = '\n'.join(lines)
    out_lines = []
    for line in t.splitlines():
        stripped = line.strip()
        if re.match(r'^\|[\s:|-]+\|$', stripped):
            continue
        if stripped.startswith('|') and stripped.endswith('|'):
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            out_lines.append(': '.join(c for c in cells if c))
        else:
            out_lines.append(line)
    t = '\n'.join(out_lines)
    t = re.sub(r'</?kbd>', '', t)
    t = re.sub(r'</?sub>', '', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'\1', t)
    t = re.sub(r'`([^`]+)`', r'\1', t)
    t = re.sub(r'^#{1,6}\s*', '', t, flags=re.M)
    t = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', t)
    t = re.sub(r'^\s*[-*]\s+', '', t, flags=re.M)
    t = re.sub(r'(?<!\w)\*([^*\n]+)\*(?!\w)', r'\1', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def extract_manifest_addon_version(text):
    m = re.search(r'^##\s*AddOnVersion:\s*(\d+)', text, re.M)
    return m.group(1) if m else None


def find_addon_version_mentions(text):
    mentions = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if 'addonversion' not in line.lower():
            continue
        for m in re.finditer(r'\d{5,}', line):
            mentions.append((lineno, m.group(0)))
    return mentions


def diff_preview(a, b, name_a, name_b, limit=60):
    diff = list(difflib.unified_diff(
        re.findall(r'.{1,100}(?:\s|$)', a),
        re.findall(r'.{1,100}(?:\s|$)', b),
        lineterm='', fromfile=name_a, tofile=name_b
    ))
    return diff[:limit]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bbcode-file', default='')
    parser.add_argument('--github-file', default='README.md')
    parser.add_argument('--bethesda-file', default='')
    parser.add_argument('--ignore-file', default='.github/description-ignore.txt')
    parser.add_argument('--manifest-file', default='')
    args = parser.parse_args()

    bbcode_path = resolve_platform_file(args.bbcode_file, 'README', 'bbcode')
    github_path = args.github_file
    bethesda_path = resolve_platform_file(args.bethesda_file, 'README', 'commonmark')
    ignore_file = args.ignore_file

    ignore_patterns = load_ignore_patterns(ignore_file)

    bbcode_raw = read(bbcode_path)
    github_raw = read(github_path)
    bethesda_raw = read(bethesda_path)

    out = ["## Description content comparison (formatting ignored)", ""]

    addon_version_problems = []
    if args.manifest_file:
        manifest_text = read(args.manifest_file)
        if manifest_text is None:
            addon_version_problems.append(f"manifest ({args.manifest_file}): file not found")
        else:
            real_version = extract_manifest_addon_version(manifest_text)
            if real_version is None:
                addon_version_problems.append(f"manifest ({args.manifest_file}): no '## AddOnVersion:' field found")
            else:
                for label, path, raw in [("BBCode", bbcode_path, bbcode_raw), ("GitHub", github_path, github_raw), ("Bethesda", bethesda_path, bethesda_raw)]:
                    if raw is None:
                        continue
                    for lineno, mentioned in find_addon_version_mentions(raw):
                        if mentioned != real_version:
                            addon_version_problems.append(f"{label} ({path}:{lineno}): mentions AddOnVersion {mentioned}, manifest's real AddOnVersion is {real_version}")

        out.append("## AddOnVersion staleness check")
        out.append("")
        if addon_version_problems:
            for p in addon_version_problems:
                out.append(f"- {p}")
                print(f"::error::{p}")
        else:
            out.append(f"No stale AddOnVersion mentions found (manifest: {args.manifest_file}).")
        out.append("")

    if ignore_patterns:
        out.append(f"Ignoring {len(ignore_patterns)} known platform-specific pattern(s) from `{ignore_file}` (e.g. donation links, legal boilerplate that isn't meant to appear on every platform).")
        out.append("")

    missing = [name for name, raw in [("BBCode", bbcode_raw), ("GitHub", github_raw), ("Bethesda", bethesda_raw)] if raw is None]
    if missing:
        out.append(f"Could not read: {', '.join(missing)} - skipping comparison.")
        print('\n'.join(out))
        if addon_version_problems:
            sys.exit(1)
        return

    bbcode = flatten_bbcode(bbcode_raw, ignore_patterns)
    github = flatten_github_md(github_raw, ignore_patterns)
    bethesda = flatten_plain_md(bethesda_raw, ignore_patterns)

    pairs = [
        ("BBCode", bbcode, "GitHub", github),
        ("GitHub", github, "Bethesda", bethesda),
        ("BBCode", bbcode, "Bethesda", bethesda),
    ]

    for name_a, a, name_b, b in pairs:
        ratio = difflib.SequenceMatcher(None, a, b).ratio()
        out.append(f"**{name_a} vs {name_b}: {ratio*100:.1f}% similar**")
        if ratio < 0.99:
            out.append("")
            out.append(f"<details><summary>Show a rough diff ({name_a} vs {name_b})</summary>")
            out.append("")
            out.append("```diff")
            out.extend(diff_preview(a, b, name_a, name_b))
            out.append("```")
            out.append("</details>")
        out.append("")

    out.append("Some wording variation between platforms is normal and expected here - this is a similarity score, not an exact-match check like the changelog comparison.")

    print('\n'.join(out))

    if addon_version_problems:
        sys.exit(1)


if __name__ == '__main__':
    main()
