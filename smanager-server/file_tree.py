"""安全路径解析与文件树。"""

from typing import List, Optional
from pathlib import Path

from fastapi import HTTPException

from models import AppConfig, TreeListEntry, TreeNode


def resolve_root(config: AppConfig, root_key: str) -> tuple[str, Path]:
    roots = config.file_tree.roots
    if root_key not in roots:
        raise HTTPException(status_code=404, detail=f"未知根目录: {root_key}")
    spec = roots[root_key]
    base = Path(config.paths.project_root) if not Path(spec.path).is_absolute() else Path("/")
    resolved = (base / spec.path).resolve() if not Path(spec.path).is_absolute() else Path(spec.path).resolve()
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"根目录不存在: {resolved}")
    return root_key, resolved


def resolve_subpath(root_path: Path, subpath: str = "") -> Path:
    if subpath in ("", ".", "/"):
        return root_path
    candidate = (root_path / subpath).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="路径越界") from exc
    if ".." in Path(subpath).parts:
        raise HTTPException(status_code=403, detail="禁止路径穿越")
    return candidate


def list_directory(config: AppConfig, root_key: str, subpath: str = "") -> list[TreeListEntry]:
    _, root_path = resolve_root(config, root_key)
    target = resolve_subpath(root_path, subpath)
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="目标不是目录")

    entries: list[TreeListEntry] = []
    try:
        children = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail="无读取权限") from exc

    rel_base = "" if subpath in ("", ".", "/") else subpath.strip("/")
    for child in children:
        if child.name.startswith("."):
            continue
        rel = f"{rel_base}/{child.name}" if rel_base else child.name
        stat = child.stat()
        entries.append(
            TreeListEntry(
                name=child.name,
                path=rel,
                type="directory" if child.is_dir() else "file",
                size=None if child.is_dir() else stat.st_size,
                mtime=stat.st_mtime,
            )
        )
    return entries


def build_tree(
    config: AppConfig,
    root_key: str,
    subpath: str = "",
    depth: int = 2,
    max_entries: int = 200,
) -> TreeNode:
    _, root_path = resolve_root(config, root_key)
    target = resolve_subpath(root_path, subpath)
    if not target.exists():
        raise HTTPException(status_code=404, detail="路径不存在")

    rel_name = target.name if subpath else root_key
    rel_path = subpath.strip("/") if subpath else ""

    if target.is_file():
        stat = target.stat()
        return TreeNode(
            name=rel_name,
            path=rel_path,
            type="file",
            size=stat.st_size,
            mtime=stat.st_mtime,
        )

    return _build_dir_node(target, rel_name, rel_path, depth, max_entries)


def _build_dir_node(
    path: Path,
    name: str,
    rel_path: str,
    depth: int,
    max_entries: int,
) -> TreeNode:
    children: Optional[List[TreeNode]] = None
    if depth > 0:
        children = []
        try:
            items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            items = []
        for child in items[:max_entries]:
            if child.name.startswith("."):
                continue
            child_rel = f"{rel_path}/{child.name}" if rel_path else child.name
            if child.is_dir():
                children.append(
                    _build_dir_node(child, child.name, child_rel, depth - 1, max_entries)
                )
            else:
                stat = child.stat()
                children.append(
                    TreeNode(
                        name=child.name,
                        path=child_rel,
                        type="file",
                        size=stat.st_size,
                        mtime=stat.st_mtime,
                    )
                )
    stat = path.stat()
    return TreeNode(
        name=name,
        path=rel_path,
        type="directory",
        size=None,
        mtime=stat.st_mtime,
        children=children,
    )


def resolve_download_path(config: AppConfig, root_key: str, subpath: str) -> Path:
    _, root_path = resolve_root(config, root_key)
    target = resolve_subpath(root_path, subpath)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")
    return target


def _is_tail_allowed(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in {".log", ".out", ".err", ".txt", ".jsonl"}:
        return True
    # WRF rsl.error.0000 / rsl.out.0000 等无常规后缀的日志
    if path.name.startswith("rsl."):
        return True
    return False


def tail_log_file(config: AppConfig, root_key: str, subpath: str, lines: int = 100) -> tuple[list[str], bool]:
    path = resolve_download_path(config, root_key, subpath)
    if not _is_tail_allowed(path):
        raise HTTPException(status_code=400, detail="仅允许读取日志类文件")
    lines = max(1, min(lines, 2000))
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            content = handle.readlines()
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"读取失败: {exc}") from exc
    truncated = len(content) > lines
    return [line.rstrip("\n") for line in content[-lines:]], truncated


def is_writable_root(config: AppConfig, root_key: str) -> bool:
    roots = config.file_tree.roots
    if root_key not in roots:
        return False
    return roots[root_key].writable


def ensure_staging_dir(config: AppConfig) -> Path:
    staging = Path(config.paths.fnl_staging)
    staging.mkdir(parents=True, exist_ok=True)
    return staging


def ensure_state_dir() -> Path:
    state = Path(__file__).resolve().parent / "state"
    state.mkdir(parents=True, exist_ok=True)
    return state
