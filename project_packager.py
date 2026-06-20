#!/usr/bin/env python3
"""
Create a Windows/macOS-safe copy of a project folder.

The original folder is never renamed in place. This tool builds a normalized
copy, records every path mapping, verifies the copied tree for Windows/macOS
filename risks, and emits an After Effects ExtendScript that can relink copied
AEP files to their normalized local assets and collect external references.
"""

from __future__ import annotations

import argparse
import ctypes
import csv
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import unicodedata


WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

WINDOWS_INVALID_CHARS = set('<>:"/\\|?*')
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
WHITESPACE_RE = re.compile(r"\s+")
UNDERSCORE_RE = re.compile(r"_+")

DEFAULT_EXCLUDES = [
    ".DS_Store",
    "._*",
    "Thumbs.db",
    "desktop.ini",
    "~$*",
    "~ai-*.tmp",
    "*.tmp",
]

try:
    _LIBC = ctypes.CDLL("libSystem.dylib")
    _CLONEFILE = _LIBC.clonefile
    _CLONEFILE.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
    _CLONEFILE.restype = ctypes.c_int
except Exception:
    _CLONEFILE = None

TEXT_EXTENSIONS = {
    ".aepx",
    ".asmdef",
    ".asset",
    ".cginc",
    ".compute",
    ".controller",
    ".cs",
    ".css",
    ".editorconfig",
    ".hlsl",
    ".inputactions",
    ".json",
    ".mat",
    ".meta",
    ".prefab",
    ".scenetemplate",
    ".shader",
    ".shadergraph",
    ".shadersubgraph",
    ".svg",
    ".txt",
    ".unity",
    ".uxml",
    ".uss",
    ".xml",
    ".yaml",
    ".yml",
}

AE_MEDIA_EXTENSIONS = {
    ".ai",
    ".aif",
    ".aiff",
    ".exr",
    ".gif",
    ".jpeg",
    ".jpg",
    ".mov",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".psb",
    ".psd",
    ".svg",
    ".tga",
    ".tif",
    ".tiff",
    ".wav",
}


def sha8(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", "surrogateescape")).hexdigest()[:8]


def split_suffixes(name: str) -> tuple[str, str]:
    if name in {".", ".."}:
        return name, ""
    if name.startswith(".") and name.count(".") == 1:
        return name, ""
    if "." not in name.rstrip("."):
        return name, ""
    stem, suffix = name.rsplit(".", 1)
    return stem, "." + suffix


def sanitize_segment(name: str, *, max_len: int = 140, replace_spaces: bool = True) -> tuple[str, list[str]]:
    reasons: list[str] = []
    original = name
    name = unicodedata.normalize("NFC", name)
    if name != original:
        reasons.append("unicode_normalized_nfc")

    changed_chars = []
    out = []
    for ch in name:
        if ch in WINDOWS_INVALID_CHARS or CONTROL_RE.match(ch):
            out.append("_")
            changed_chars.append(ch)
        else:
            out.append(ch)
    name = "".join(out)
    if changed_chars:
        reasons.append("windows_invalid_chars")

    if replace_spaces and WHITESPACE_RE.search(name):
        name = WHITESPACE_RE.sub("_", name)
        reasons.append("whitespace_to_underscore")

    trimmed = name.strip(" .")
    if trimmed != name:
        reasons.append("trimmed_edge_space_or_dot")
        name = trimmed

    name = UNDERSCORE_RE.sub("_", name)
    if name in {"", ".", ".."}:
        name = f"unnamed_{sha8(original)}"
        reasons.append("empty_or_dot_name")

    stem, suffix = split_suffixes(name)
    if stem.upper() in WINDOWS_RESERVED_NAMES:
        stem = f"{stem}_file"
        name = stem + suffix
        reasons.append("windows_reserved_name")

    if len(name) > max_len:
        stem, suffix = split_suffixes(name)
        budget = max(12, max_len - len(suffix) - 9)
        name = f"{stem[:budget]}_{sha8(original)}{suffix}"
        reasons.append("segment_truncated")

    return name, reasons


def is_excluded(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def rel_posix(path: Path) -> str:
    return path.as_posix()


def jsonable_path(path: Path) -> str:
    return str(path)


class Planner:
    def __init__(
        self,
        source: Path,
        dest: Path,
        excludes: list[str],
        replace_spaces: bool,
        max_segment_len: int,
    ) -> None:
        self.source = source
        self.dest = dest
        self.excludes = excludes
        self.replace_spaces = replace_spaces
        self.max_segment_len = max_segment_len
        self.entries: list[dict] = []
        self.renames: list[dict] = []
        self.skipped: list[dict] = []
        self.collisions: list[dict] = []
        self.warnings: list[dict] = []

    def build(self) -> None:
        if not self.source.exists() or not self.source.is_dir():
            raise SystemExit(f"Source is not a directory: {self.source}")
        if self.dest.exists():
            raise SystemExit(f"Destination already exists; refusing to overwrite: {self.dest}")
        self._walk(Path(""), Path(""))

    def _walk(self, src_rel_dir: Path, dst_rel_dir: Path) -> None:
        abs_dir = self.source / src_rel_dir
        try:
            children = sorted(os.scandir(abs_dir), key=lambda e: e.name.casefold())
        except OSError as exc:
            self.warnings.append({"path": rel_posix(src_rel_dir), "warning": f"cannot_scan: {exc}"})
            return

        used_casefold: dict[str, str] = {}
        planned_children: list[tuple[os.DirEntry, Path]] = []

        for child in children:
            if is_excluded(child.name, self.excludes):
                self.skipped.append({"path": rel_posix(src_rel_dir / child.name), "reason": "excluded"})
                continue

            safe_name, reasons = sanitize_segment(
                child.name,
                max_len=self.max_segment_len,
                replace_spaces=self.replace_spaces,
            )
            candidate = safe_name
            fold = candidate.casefold()
            if fold in used_casefold:
                stem, suffix = split_suffixes(safe_name)
                candidate = f"{stem}__dup_{sha8((src_rel_dir / child.name).as_posix())}{suffix}"
                fold = candidate.casefold()
                self.collisions.append(
                    {
                        "directory": rel_posix(src_rel_dir),
                        "original": child.name,
                        "first_target": used_casefold.get(safe_name.casefold(), ""),
                        "resolved_target": candidate,
                    }
                )
            used_casefold[fold] = candidate

            src_rel = src_rel_dir / child.name
            dst_rel = dst_rel_dir / candidate
            entry = {
                "type": "dir" if child.is_dir(follow_symlinks=False) else "file",
                "source_rel": rel_posix(src_rel),
                "dest_rel": rel_posix(dst_rel),
                "source_abs": jsonable_path(self.source / src_rel),
                "dest_abs": jsonable_path(self.dest / dst_rel),
                "renamed": child.name != candidate,
                "reasons": reasons,
                "is_symlink": child.is_symlink(),
            }
            self.entries.append(entry)
            if entry["renamed"]:
                self.renames.append(entry)
            planned_children.append((child, src_rel, dst_rel))

        for child, src_rel, dst_rel in planned_children:
            if child.is_dir(follow_symlinks=False):
                self._walk(Path(src_rel), Path(dst_rel))


def copy_tree(planner: Planner, progress_callback=None) -> None:
    planner.dest.mkdir(parents=True)
    dirs = [e for e in planner.entries if e["type"] == "dir"]
    files = [e for e in planner.entries if e["type"] == "file"]

    for entry in dirs:
        Path(entry["dest_abs"]).mkdir(parents=True, exist_ok=True)

    total_files = len(files)
    for index, entry in enumerate(files, start=1):
        src = Path(entry["source_abs"])
        dst = Path(entry["dest_abs"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        if entry["is_symlink"]:
            target = os.readlink(src)
            os.symlink(target, dst)
        else:
            copy_file(src, dst)
        if progress_callback is not None:
            progress_callback(index, total_files, entry)
        if index == 1 or index % 100 == 0 or index == total_files:
            print(f"copied {index}/{total_files}: {entry['source_rel']} -> {entry['dest_rel']}", flush=True)


def copy_file(src: Path, dst: Path) -> None:
    if _CLONEFILE is not None:
        result = _CLONEFILE(
            os.fsencode(str(src)),
            os.fsencode(str(dst)),
            0,
        )
        if result == 0:
            shutil.copystat(src, dst, follow_symlinks=False)
            return
    shutil.copy2(src, dst)


def scan_tree_risks(root: Path, *, max_path_len: int = 240) -> list[dict]:
    issues: list[dict] = []
    seen_by_dir: dict[str, dict[str, str]] = {}
    for current, dirs, files in os.walk(root):
        current_path = Path(current)
        names = dirs + files
        local_seen: dict[str, str] = {}
        for name in names:
            rel = (current_path / name).relative_to(root)
            safe, reasons = sanitize_segment(name, replace_spaces=True)
            if name != safe:
                issues.append({"path": rel_posix(rel), "issue": "unsafe_name_after_copy", "suggested": safe, "reasons": reasons})
            if name.rstrip(" .") != name:
                issues.append({"path": rel_posix(rel), "issue": "trailing_space_or_dot"})
            stem, _suffix = split_suffixes(name)
            if stem.upper() in WINDOWS_RESERVED_NAMES:
                issues.append({"path": rel_posix(rel), "issue": "windows_reserved_name"})
            fold = name.casefold()
            if fold in local_seen:
                issues.append({"path": rel_posix(rel), "issue": "case_insensitive_collision", "other": local_seen[fold]})
            local_seen[fold] = rel_posix(rel)
            if len(str(rel)) > max_path_len:
                issues.append({"path": rel_posix(rel), "issue": "long_relative_path", "length": len(str(rel))})
        seen_by_dir[str(current_path)] = local_seen
    return issues


def unity_meta_issues(source: Path, planner: Planner) -> list[dict]:
    mapping = {entry["source_rel"]: entry["dest_rel"] for entry in planner.entries}
    issues: list[dict] = []
    for source_rel, dest_rel in mapping.items():
        if not source_rel.endswith(".meta"):
            continue
        asset_rel = source_rel[:-5]
        if asset_rel not in mapping:
            continue
        expected_meta = mapping[asset_rel] + ".meta"
        if dest_rel != expected_meta:
            issues.append(
                {
                    "source_meta": source_rel,
                    "dest_meta": dest_rel,
                    "expected_dest_meta": expected_meta,
                }
            )
    return issues


def collect_project_files(planner: Planner) -> dict[str, list[str]]:
    buckets = {
        "after_effects": [],
        "after_effects_xml": [],
        "illustrator": [],
        "photoshop": [],
        "unity_scenes": [],
        "unity_prefabs": [],
        "unity_assets": [],
    }
    for entry in planner.entries:
        if entry["type"] != "file":
            continue
        suffix = Path(entry["dest_rel"]).suffix.lower()
        dest = entry["dest_abs"]
        if suffix == ".aep":
            buckets["after_effects"].append(dest)
        elif suffix == ".aepx":
            buckets["after_effects_xml"].append(dest)
        elif suffix == ".ai":
            buckets["illustrator"].append(dest)
        elif suffix in {".psd", ".psb"}:
            buckets["photoshop"].append(dest)
        elif suffix == ".unity":
            buckets["unity_scenes"].append(dest)
        elif suffix == ".prefab":
            buckets["unity_prefabs"].append(dest)
        elif suffix in {".asset", ".mat", ".controller"}:
            buckets["unity_assets"].append(dest)
    return buckets


def write_reports(planner: Planner, report_dir: Path, executed: bool) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "source": str(planner.source),
        "destination": str(planner.dest),
        "executed": executed,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_entries": len(planner.entries),
        "renamed_entries": len(planner.renames),
        "skipped_entries": len(planner.skipped),
        "collision_resolutions": len(planner.collisions),
        "project_files": collect_project_files(planner),
        "unity_meta_pair_issues": unity_meta_issues(planner.source, planner),
        "post_copy_risks": scan_tree_risks(planner.dest) if executed and planner.dest.exists() else [],
        "warnings": planner.warnings,
    }

    (report_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (report_dir / "rename_map.json").write_text(json.dumps(planner.renames, indent=2, ensure_ascii=False), encoding="utf-8")
    (report_dir / "skipped.json").write_text(json.dumps(planner.skipped, indent=2, ensure_ascii=False), encoding="utf-8")
    (report_dir / "collisions.json").write_text(json.dumps(planner.collisions, indent=2, ensure_ascii=False), encoding="utf-8")

    with (report_dir / "rename_map.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["type", "source_rel", "dest_rel", "reasons"])
        writer.writeheader()
        for entry in planner.renames:
            writer.writerow(
                {
                    "type": entry["type"],
                    "source_rel": entry["source_rel"],
                    "dest_rel": entry["dest_rel"],
                    "reasons": ";".join(entry["reasons"]),
                }
            )

    write_ae_script(planner, report_dir / "ae_relink_collect.jsx")


def js_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def write_ae_script(planner: Planner, script_path: Path) -> None:
    media_map = {}
    ae_projects = []
    for entry in planner.entries:
        if entry["type"] != "file":
            continue
        suffix = Path(entry["dest_rel"]).suffix.lower()
        if suffix == ".aep":
            ae_projects.append(entry["dest_abs"])
        if suffix in AE_MEDIA_EXTENSIONS:
            media_map[entry["source_abs"]] = entry["dest_abs"]

    lines = [
        "// Generated by cross_platform_project_packager.py",
        "// Run this in After Effects after the normalized copy has been created.",
        "// It opens only copied .aep files, relinks known copied media, collects external media into _Collected_References, and saves the copied projects.",
        "",
        "var AE_PROJECTS = [",
    ]
    lines.extend(f"  {js_string(path)}," for path in ae_projects)
    lines.extend([
        "];",
        "var MEDIA_MAP = {",
    ])
    lines.extend(f"  {js_string(src)}: {js_string(dst)}," for src, dst in sorted(media_map.items()))
    lines.extend([
        "};",
        f"var DEST_ROOT = {js_string(str(planner.dest))};",
        "var REPORT_LINES = [];",
        "",
        "function safeName(name) {",
        "  var out = name.replace(/[<>:\"/\\\\|?*\\x00-\\x1F\\x7F]/g, '_').replace(/\\s+/g, '_').replace(/^[ .]+|[ .]+$/g, '').replace(/_+/g, '_');",
        "  if (!out || out === '.' || out === '..') out = 'unnamed_asset';",
        "  return out;",
        "}",
        "",
        "function ensureFolder(folder) {",
        "  if (!folder.exists) folder.create();",
        "}",
        "",
        "function collectName(folder, name) {",
        "  var base = safeName(name);",
        "  var f = new File(folder.fsName + '/' + base);",
        "  var i = 1;",
        "  while (f.exists) {",
        "    var dot = base.lastIndexOf('.');",
        "    var stem = dot >= 0 ? base.substring(0, dot) : base;",
        "    var ext = dot >= 0 ? base.substring(dot) : '';",
        "    f = new File(folder.fsName + '/' + stem + '_copy' + i + ext);",
        "    i++;",
        "  }",
        "  return f;",
        "}",
        "",
        "function relinkProject(projectPath) {",
        "  var projectFile = new File(projectPath);",
        "  if (!projectFile.exists) { REPORT_LINES.push('MISSING_PROJECT\\t' + projectPath); return; }",
        "  app.open(projectFile);",
        "  var projectFolder = new Folder(DEST_ROOT + '/_Collected_References/' + safeName(projectFile.displayName.replace(/\\.aep$/i, '')));",
        "  ensureFolder(new Folder(DEST_ROOT + '/_Collected_References'));",
        "  ensureFolder(projectFolder);",
        "  for (var i = 1; i <= app.project.numItems; i++) {",
        "    var item = app.project.item(i);",
        "    if (!(item instanceof FootageItem) || !item.file) continue;",
        "    var oldPath = item.file.fsName;",
        "    var targetPath = MEDIA_MAP[oldPath];",
        "    var targetFile = targetPath ? new File(targetPath) : null;",
        "    if (targetFile && targetFile.exists) {",
        "      item.replace(targetFile);",
        "      REPORT_LINES.push('RELINKED_LOCAL\\t' + projectPath + '\\t' + oldPath + '\\t' + targetFile.fsName);",
        "      continue;",
        "    }",
        "    var oldFile = new File(oldPath);",
        "    if (oldFile.exists) {",
        "      var copied = collectName(projectFolder, oldFile.displayName);",
        "      if (oldFile.copy(copied.fsName)) {",
        "        item.replace(copied);",
        "        REPORT_LINES.push('COLLECTED_EXTERNAL\\t' + projectPath + '\\t' + oldPath + '\\t' + copied.fsName);",
        "      } else {",
        "        REPORT_LINES.push('COPY_FAILED\\t' + projectPath + '\\t' + oldPath);",
        "      }",
        "    } else {",
        "      REPORT_LINES.push('MISSING_FOOTAGE\\t' + projectPath + '\\t' + oldPath);",
        "    }",
        "  }",
        "  app.project.save(projectFile);",
        "  app.project.close(CloseOptions.DO_NOT_SAVE_CHANGES);",
        "}",
        "",
        "app.beginSuppressDialogs();",
        "for (var p = 0; p < AE_PROJECTS.length; p++) relinkProject(AE_PROJECTS[p]);",
        "app.endSuppressDialogs(false);",
        "var report = new File(DEST_ROOT + '/_CrossPlatformReport/ae_relink_report.tsv');",
        "report.encoding = 'UTF-8';",
        "report.open('w');",
        "for (var r = 0; r < REPORT_LINES.length; r++) report.writeln(REPORT_LINES[r]);",
        "report.close();",
    ])
    script_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a cross-platform-safe project folder copy.")
    parser.add_argument("--source", required=True, help="Source folder to copy.")
    parser.add_argument("--dest", required=True, help="Destination folder to create.")
    parser.add_argument("--execute", action="store_true", help="Actually create the copy. Without this, only reports are generated.")
    parser.add_argument("--report-dir", help="Report directory. Defaults to DEST/_CrossPlatformReport or /tmp for dry-run.")
    parser.add_argument("--keep-spaces", action="store_true", help="Keep spaces in names. By default whitespace is normalized to underscores.")
    parser.add_argument("--max-segment-len", type=int, default=140, help="Maximum filename segment length after normalization.")
    parser.add_argument("--exclude", action="append", default=[], help="Additional fnmatch pattern to exclude.")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    dest = Path(args.dest).expanduser().resolve()
    excludes = DEFAULT_EXCLUDES + args.exclude

    planner = Planner(
        source=source,
        dest=dest,
        excludes=excludes,
        replace_spaces=not args.keep_spaces,
        max_segment_len=args.max_segment_len,
    )
    planner.build()

    if args.execute:
        copy_tree(planner)

    if args.report_dir:
        report_dir = Path(args.report_dir).expanduser().resolve()
    elif args.execute:
        report_dir = dest / "_CrossPlatformReport"
    else:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        report_dir = Path("/tmp") / f"cross_platform_project_report_{stamp}"

    write_reports(planner, report_dir, executed=args.execute)

    print(json.dumps(
        {
            "source": str(source),
            "destination": str(dest),
            "executed": args.execute,
            "report_dir": str(report_dir),
            "total_entries": len(planner.entries),
            "renamed_entries": len(planner.renames),
            "skipped_entries": len(planner.skipped),
            "collision_resolutions": len(planner.collisions),
        },
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
