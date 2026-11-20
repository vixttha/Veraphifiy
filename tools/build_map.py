#!/usr/bin/env python3
"""Render a read-only Provenistem catalog from an exact Git commit."""
import argparse
import base64
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

from library import MAX_JSON_DEPTH, MAX_RECORD_BYTES, MAX_RECORD_FILES, safe_repo_path, within_depth

ROOT = Path(__file__).resolve().parent
SECTIONS = {"ideas": "IDEA", "features": "FEAT"}
OTHER = "uncategorized"
TEMPLATE = ROOT / "map-view.html"


def git(repo, *args):
    proc = subprocess.run(["git", "--literal-pathspecs", "--no-replace-objects", "-C", str(repo), *args],
                          capture_output=True)
    if proc.returncode:
        raise ValueError(proc.stderr.decode("utf-8", "replace").strip() or f"Git {args[0]} failed")
    return proc.stdout


def json_object(raw, path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate field {key!r}")
            result[key] = value
        return result

    def finite(value):
        raise ValueError(f"invalid JSON constant {value!r}")

    try:
        if len(raw) > MAX_RECORD_BYTES:
            raise ValueError("JSON size exceeds catalog limit")
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique, parse_constant=finite)
        if not isinstance(value, dict) or not within_depth(value, MAX_JSON_DEPTH):
            raise ValueError("expected a bounded JSON object")
        return value
    except (ValueError, RecursionError) as error:
        raise ValueError(f"{path}: {error}") from error


def read_records(repo, pin, prefix):
    records = {}
    for kind, code in SECTIONS.items():
        folder = f"{prefix}{kind}/records"
        if git(repo, "cat-file", "-t", f"{pin}:{folder}").strip() != b"tree":
            raise ValueError(f"{folder}: expected a committed records directory")
        entries = git(repo, "ls-tree", "-z", "-r", "-l", pin, "--", folder).split(b"\0")
        if len(entries) - 1 > MAX_RECORD_FILES:
            raise ValueError(f"{folder}: too many record entries")
        for entry in entries[:-1]:
            header, path = entry.decode("utf-8").split("\t", 1)
            mode, obj, blob, size = header.split()
            if mode not in ("100644", "100755") or obj != "blob":
                raise ValueError(f"{path}: expected a regular Git blob")
            if path == f"{folder}/.gitkeep":
                continue
            name = re.fullmatch(rf"{re.escape(folder)}/({code}-[0-9]{{6}})\.json", path)
            if not name or int(size) > MAX_RECORD_BYTES:
                raise ValueError(f"{path}: unexpected record path or oversized record")
            raw = json_object(git(repo, "cat-file", "blob", blob), path)
            ident = name[1]
            if raw.get("schema_version") != 1 or type(raw.get("schema_version")) is not int or raw.get("id") != ident:
                raise ValueError(f"{path}: expected schema version 1 and matching record ID")
            for key in ("title", "summary", "lifecycle_status", "implementation_status"):
                if not isinstance(raw.get(key), str) or not raw[key].strip():
                    raise ValueError(f"{path}: {key} must be a nonempty string")
            field = "related_ideas" if kind == "ideas" else "idea_ids"
            refs = raw.get(field)
            if (not isinstance(refs, list) or any(not isinstance(x, str) for x in refs)
                    or len(set(refs)) != len(refs)):
                raise ValueError(f"{path}: {field} must contain distinct string IDs")
            testing = raw.get("testing", {})
            if not isinstance(testing, dict) or (testing.get("status") is not None and
                                                 not isinstance(testing["status"], str)):
                raise ValueError(f"{path}: testing.status must be a string when present")
            release = raw.get("release_membership") if kind == "features" else None
            if release is not None and not isinstance(release, str):
                raise ValueError(f"{path}: release_membership must be a string")
            record = {"id": ident, "path": path, "kind": kind, "title": raw["title"], "summary": raw["summary"],
                      "lifecycle": raw["lifecycle_status"], "implementation": raw["implementation_status"],
                      "testing": testing.get("status"), "release": release}
            if kind == "ideas":
                record.update(related=sorted(refs), incoming=[], citing=[])
            else:
                record["origins"] = sorted(refs)
            records[ident] = record
    for record in records.values():
        idea = record["kind"] == "ideas"
        for ref in record["related" if idea else "origins"]:
            if ref == record["id"] or ref not in records or records[ref]["kind"] != "ideas":
                raise ValueError(f'{record["path"]}: unresolved or self-referential idea {ref!r}')
            records[ref]["incoming" if idea else "citing"].append(record["id"])
    return records


def build_groups(config, records):
    groups, assigned = [], set()
    seen_groups = {OTHER}
    configured = config.get("groups", [])
    if not isinstance(configured, list) or len(configured) > 50:
        raise ValueError("groups must be a list with at most 50 entries")
    for group in configured:
        if not isinstance(group, dict):
            raise ValueError("each group must be an object")
        ident, label, description = (group.get(key) for key in ("id", "label", "description"))
        if (not isinstance(ident, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,30}", ident)
                or ident in seen_groups or ident == "overview"):
            raise ValueError(f"invalid or repeated group ID {ident!r}")
        for key, value, limit in (("label", label, 40), ("description", description, 160)):
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError(f"group {ident}: invalid {key}")
        seen_groups.add(ident)
        group_data = {"id": ident, "label": label, "description": description}
        for kind in SECTIONS:
            ids = group.get(kind, [])
            if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids):
                raise ValueError(f"group {ident}: {kind} must be a list of IDs")
            for rid in ids:
                if rid in assigned or rid not in records or records[rid]["kind"] != kind:
                    raise ValueError(f"group {ident}: unknown, repeated, or wrong-kind record {rid!r}")
                records[rid]["group"] = ident
                assigned.add(rid)
            group_data[kind] = sorted(ids)
        groups.append(group_data)
    ungrouped = {"id": OTHER, "label": "Uncategorized", "description": "Records without a browsing category.",
                 "ideas": [], "features": []}
    for ident, record in records.items():
        if ident not in assigned:
            record["group"] = OTHER
            ungrouped[record["kind"]].append(ident)
    if not groups or len(assigned) < len(records):
        groups.append(ungrouped)
    return groups


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(data, **options):
    return json.dumps(data, ensure_ascii=True, sort_keys=True, allow_nan=False, **options)


def render(catalog):
    template = TEMPLATE.read_text(encoding="utf-8")
    scripts = re.findall(r"<script>([\s\S]*?)</script>", template)
    if len(scripts) != 1 or template.count("__CATALOG__") != 1 or template.count("__SCRIPT_HASH__") != 1:
        raise ValueError("map-view.html is missing its expected template slots")
    script_hash = base64.b64encode(hashlib.sha256(scripts[0].encode()).digest()).decode()
    raw = encoded(catalog, separators=(",", ":")).replace("<", "\\u003c")
    return template.replace("__SCRIPT_HASH__", script_hash).replace("__CATALOG__", raw).encode("utf-8")


def build(args):
    repo = Path(args.repo)
    if args.catalog_path != "." and not safe_repo_path(args.catalog_path):
        raise ValueError("catalog path must be a repository-relative path")
    if args.github_repo and not re.fullmatch(r"[A-Za-z0-9-]+/(?!\.\.?$)[A-Za-z0-9_.-]+", args.github_repo):
        raise ValueError("GitHub repository must be OWNER/REPOSITORY")
    pin = git(repo, "rev-parse", "--verify", "--end-of-options", args.rev + "^{commit}").decode().strip()
    prefix = "" if args.catalog_path == "." else args.catalog_path + "/"
    records = read_records(repo, pin, prefix)
    config = {}
    if args.groups:
        if not safe_repo_path(args.groups):
            raise ValueError("groups path must be relative to the selected catalog")
        path = prefix + args.groups
        listing = git(repo, "ls-tree", "-l", pin, "--", path).decode().split("\t", 1)[0].split()
        if len(listing) != 4 or listing[0] not in ("100644", "100755") or listing[1] != "blob":
            raise ValueError(f"{path}: expected a committed group configuration file")
        if int(listing[3]) > MAX_RECORD_BYTES:
            raise ValueError(f"{path}: oversized group configuration")
        config = json_object(git(repo, "show", f"{pin}:{path}"), path)
    title = config.get("title", "Provenistem catalog")
    if not isinstance(title, str) or not title.strip() or len(title) > 60:
        raise ValueError("catalog title must contain 1–60 characters")
    groups = build_groups(config, records)
    base = "https://github.com/" + args.github_repo if args.github_repo else None
    counts = {"ideas": 0, "features": 0, "idea_references": 0, "feature_to_idea": 0}
    for record in records.values():
        counts[record["kind"]] += 1
        counts["idea_references"] += len(record.get("related", []))
        counts["feature_to_idea"] += len(record.get("origins", []))
        record["url"] = f'{base}/blob/{pin}/{quote(record["path"])}' if base else None
    data = {"title": title, "revision": pin, "catalog_path": args.catalog_path, "groups": groups,
            "records": list(records.values()), "counts": counts, "repository": args.github_repo,
            "tree": f"{base}/tree/{pin}" if base else None}
    files = {"index.html": render(data), "graph.json": (encoded(data, indent=2) + "\n").encode()}
    proof = {"source": {"revision": pin, "repository": args.github_repo, "catalog_path": args.catalog_path},
             "generator_sha256": digest(Path(__file__).read_bytes()),
             "viewer_sha256": digest(TEMPLATE.read_bytes()),
             "outputs": {name: digest(raw) for name, raw in files.items()}}
    files["receipt.json"] = (encoded(proof, indent=2) + "\n").encode()
    output = Path(args.output)
    output.mkdir()
    created = []
    try:
        for name, raw in files.items():
            path = output / name
            with path.open("xb") as handle:
                created.append(path)
                handle.write(raw)
    except OSError:
        for path in created:
            path.unlink(missing_ok=True)
        output.rmdir()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Git checkout containing the catalog")
    parser.add_argument("--rev", default="HEAD", help="Git revision to resolve and read")
    parser.add_argument("--catalog-path", default=".", help="Catalog root within the repository")
    parser.add_argument("--groups", help="Optional committed JSON path relative to the catalog")
    parser.add_argument("--github-repo", help="Optional OWNER/REPOSITORY for exact record links")
    parser.add_argument("--output", required=True, help="New output directory with an existing parent")
    args = parser.parse_args()
    try:
        build(args)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
