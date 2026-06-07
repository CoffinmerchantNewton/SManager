"""
收集 FNL 到运行目录。

选文件策略（替代「一律 ≥30MB 才有效」）：
  在主目录 + 备用目录下，枚举多种常见路径布局，收集所有存在的同名文件；
  丢弃体积 < FNL_ABSOLUTE_MIN_MB 的（明显截断/空文件）；
  在剩余候选中取**体积最大**的一个作为该时次的 FNL（可自动用备用里更完整的副本替换主目录损坏的小文件）。

路径布局（每个 root 均尝试，顺序不影响「选最大」结果）：
  1) root/YYYY/YYYYMMDD/fnl_*.grib2   （新中心镜像按日分子目录）
  2) root/YYYY/fnl_*.grib2            （年仅一层、平铺）
  3) root/YYYYMMDD/fnl_*.grib2        （仅日期目录）
  4) root/fnl_*.grib2                 （根目录平铺，少见）
"""

import os
import sys
import shutil
import argparse
from datetime import datetime, timedelta

try:
    _project = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, _project)
    import config as _cfg
    FNL_ROOT = _cfg.FNL_ROOT
    FNL_FALLBACK_ROOT = getattr(_cfg, "FNL_FALLBACK_ROOT", "") or ""
    FNL_COPY_METHOD = _cfg.FNL_COPY_METHOD
    FNL_ABSOLUTE_MIN_MB = float(getattr(_cfg, "FNL_ABSOLUTE_MIN_MB", 5.0))
except Exception:
    FNL_ROOT = "/g1/COMMONDATA/glob/fnl"
    FNL_FALLBACK_ROOT = "/g7/anxq/Zhangjt/static/fnl"
    FNL_COPY_METHOD = "symlink"
    FNL_ABSOLUTE_MIN_MB = 5.0

_ABS_MIN_BYTES = int(FNL_ABSOLUTE_MIN_MB * 1024 * 1024)


def _is_real_grib2(path):
    """grib2 magic 校验：前 4 字节必须是 'GRIB'。
    历史上遇到过主源拉到 39MB 的 HTML 错误页占位，体积达标但不是 grib2，
    会让 ungrib 报 'edition_num'。直接按 magic 排除。"""
    try:
        with open(path, "rb") as f:
            return f.read(4) == b"GRIB"
    except OSError:
        return False


def _link_or_copy(src, dst):
    if FNL_COPY_METHOD == "symlink":
        os.symlink(os.path.abspath(src), dst)
    else:
        shutil.copy2(src, dst)


def _roots_ordered():
    roots = [FNL_ROOT]
    if FNL_FALLBACK_ROOT and FNL_FALLBACK_ROOT not in roots:
        roots.append(FNL_FALLBACK_ROOT)
    return [r for r in roots if r and os.path.isdir(r)]


def _layout_paths(root, fname, day_str, year_str):
    """同一 root 下一种文件名的所有可能路径（去重保持顺序）。"""
    seq = [
        os.path.join(root, year_str, day_str, fname),
        os.path.join(root, year_str, fname),
        os.path.join(root, day_str, fname),
        os.path.join(root, fname),
    ]
    out = []
    seen = set()
    for p in seq:
        ap = os.path.normpath(p)
        if ap not in seen:
            seen.add(ap)
            out.append(ap)
    return out


def _collect_candidates(fname, day_str, year_str):
    """返回 [(path, size), ...]：必须存在 + size>=最小下限 + grib2 magic 通过。"""
    found = []
    rejected_non_grib = []
    for root in _roots_ordered():
        for p in _layout_paths(root, fname, day_str, year_str):
            if not os.path.isfile(p):
                continue
            try:
                sz = os.path.getsize(p)
            except OSError:
                continue
            if sz < _ABS_MIN_BYTES:
                continue
            if not _is_real_grib2(p):
                rejected_non_grib.append((p, sz))
                continue
            found.append((p, sz))
    if rejected_non_grib and not found:
        for p, sz in rejected_non_grib:
            print(
                f"  [FNL][skip] {p}: 大小 {sz / (1024 * 1024):.1f} MB 但非 grib2"
                f"（magic≠'GRIB'，可能为错误页占位）"
            )
    elif rejected_non_grib:
        for p, sz in rejected_non_grib:
            print(
                f"  [FNL][skip] {fname}: 跳过非 grib2 候选 {p} "
                f"({sz / (1024 * 1024):.1f} MB)"
            )
    return found


def pick_best_fnl_path(fname, day_str, year_str, log_pick=True):
    """主备多布局候选中取体积最大者；无合格候选返回 None。"""
    cands = _collect_candidates(fname, day_str, year_str)
    if not cands:
        return None
    max_sz = max(sz for _p, sz in cands)
    best = [p for p, sz in cands if sz == max_sz]
    # 同体积时：优先主源路径，再按路径字符串稳定排序
    root_abs = os.path.abspath(FNL_ROOT)

    def sort_key(p):
        under_primary = 1 if p.startswith(root_abs) else 0
        return (-under_primary, p)

    best_path = sorted(best, key=sort_key)[0]

    if log_pick and len(cands) > 1:
        smaller = [
            (p, sz)
            for p, sz in cands
            if os.path.abspath(p) != os.path.abspath(best_path) and sz < max_sz - 1024
        ]
        if smaller:
            otxt = ", ".join(f"{sz / (1024 * 1024):.1f} MB" for _p, sz in smaller[:4])
            if len(smaller) > 4:
                otxt += ", …"
            print(
                f"  [FNL] {fname}: 多副本中选用最大 "
                f"{max_sz / (1024 * 1024):.1f} MB ← {best_path}（丢弃较小: {otxt}）"
            )

    return os.path.abspath(best_path)


def validate_fnl_directory(dest_dir):
    """link_grib 前：确保每个时次指向当前策略下的最优副本。
    判定依据：路径一致 + 大小达标 + grib2 magic 通过；任一失败则重新选最佳并替换。"""
    import glob

    dest_dir = os.path.abspath(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    for dst in sorted(glob.glob(os.path.join(dest_dir, "fnl_*.grib2"))):
        base = os.path.basename(dst)
        if len(base) < 13:
            print(f"[FATAL] 无法解析 FNL 文件名: {base}")
            sys.exit(1)
        day_str = base[4:12]
        year_str = day_str[:4]
        best = pick_best_fnl_path(base, day_str, year_str, log_pick=False)
        if best is None:
            print(
                f"[FATAL] 无合格 FNL（≥{FNL_ABSOLUTE_MIN_MB} MB 且通过 grib2 magic）: "
                f"{base}，已搜索主源与备用全部布局"
            )
            sys.exit(1)
        try:
            cur = os.path.realpath(dst)
        except OSError:
            cur = ""
        cur_size = 0
        try:
            cur_size = os.path.getsize(dst)
        except OSError:
            pass
        cur_ok_grib = _is_real_grib2(dst) if cur_size >= _ABS_MIN_BYTES else False
        need_repair = (
            os.path.abspath(cur) != os.path.abspath(best)
            or cur_size < _ABS_MIN_BYTES
            or not cur_ok_grib
        )
        if need_repair:
            reason = []
            if os.path.abspath(cur) != os.path.abspath(best):
                reason.append(f"路径不一致(cur={cur})")
            if cur_size < _ABS_MIN_BYTES:
                reason.append(f"过小({cur_size/1024/1024:.1f}MB)")
            if not cur_ok_grib:
                reason.append("非 grib2(magic≠'GRIB')")
            print(f"  [repair] {base}: 重链至 {best}  原因: {', '.join(reason)}")
            try:
                os.remove(dst)
            except OSError:
                pass
            _link_or_copy(best, dst)


def copy_fnl(start_date: str, end_date: str, dest: str = "fnl"):
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    os.makedirs(dest, exist_ok=True)

    processed = 0
    current = start
    while current <= end:
        day_str = current.strftime("%Y%m%d")
        year_str = current.strftime("%Y")
        day_dir_primary = os.path.join(FNL_ROOT, year_str, day_str)

        expected = [
            f"fnl_{day_str}_{hh}_00.grib2"
            for hh in ("00", "06", "12", "18")
        ]
        primary_fnames = []
        if os.path.isdir(day_dir_primary):
            primary_fnames = [
                f for f in os.listdir(day_dir_primary) if f.endswith(".grib2")
            ]
        # Keep any extra primary files, but always try the standard four FNL cycles
        # so missing primary cycles can be supplied by the fallback root.
        fnames = sorted(set(primary_fnames).union(expected))

        for fname in fnames:
            dst = os.path.join(dest, fname)
            best = pick_best_fnl_path(fname, day_str, year_str)
            if best is None:
                print(
                    f"[FATAL] 未找到合格 FNL: {fname} (日 {day_str})，"
                    f"已搜索主源与备用全部布局（必须 ≥{FNL_ABSOLUTE_MIN_MB} MB"
                    f"且 grib2 magic 通过）"
                )
                sys.exit(1)
            if os.path.lexists(dst):
                # 已有 symlink/文件：检查是否仍是当前最佳，否则就替换。
                try:
                    cur = os.path.realpath(dst)
                except OSError:
                    cur = ""
                cur_ok = (
                    os.path.abspath(cur) == os.path.abspath(best)
                    and os.path.exists(dst)
                    and _is_real_grib2(dst)
                )
                if cur_ok:
                    continue
                print(
                    f"  replace: {fname}: 旧链接 {cur or '<无效>'} 不是当前最佳，"
                    f"重链 → {best}"
                )
                try:
                    os.remove(dst)
                except OSError:
                    pass
            _link_or_copy(best, dst)
            processed += 1
            print(
                f"  {'symlink' if FNL_COPY_METHOD == 'symlink' else 'copy'}: "
                f"{fname} ← {best}"
            )

        current += timedelta(days=1)

    print(f"\n完成，共处理 {processed} 个文件 → {os.path.abspath(dest)}")


def scan_range(start_date: str, end_date: str):
    """干跑扫描 [start, end] 范围每日 4 时次，返回 (missing, total)。
    主源 + 备份所有布局都没有合格 grib2 副本的时次记入 missing。"""
    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")
    missing = []
    total = 0
    cur = start
    while cur <= end:
        day = cur.strftime("%Y%m%d")
        year = cur.strftime("%Y")
        for hh in ("00", "06", "12", "18"):
            total += 1
            fname = f"fnl_{day}_{hh}_00.grib2"
            if pick_best_fnl_path(fname, day, year, log_pick=False) is None:
                missing.append(fname)
        cur += timedelta(days=1)
    return missing, total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="收集 FNL 数据到指定目录")
    parser.add_argument("start", help="起始日期 (YYYYMMDD)")
    parser.add_argument("end", help="结束日期 (YYYYMMDD)")
    parser.add_argument("-o", "--output", default="fnl", help="目标目录 (默认: fnl)")
    parser.add_argument(
        "--method",
        choices=["symlink", "copy"],
        default=FNL_COPY_METHOD,
        help="文件处理方式: symlink(软链接) 或 copy(实体拷贝)",
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="只扫描该范围的 FNL 是否齐全（含 grib2 magic 校验），不复制；"
             "若有缺失打印列表，正常时退出 0，缺失退出 2",
    )
    args = parser.parse_args()
    if args.scan_only:
        miss, total = scan_range(args.start, args.end)
        print(f"[FNL][scan] 范围 {args.start}~{args.end}：合计 {total} 个时次，"
              f"缺失/损坏 {len(miss)} 个")
        for m in miss:
            print(f"  MISSING {m}")
        sys.exit(2 if miss else 0)
    FNL_COPY_METHOD = args.method
    copy_fnl(args.start, args.end, args.output)
