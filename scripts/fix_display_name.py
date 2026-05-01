#!/usr/bin/env python3
"""修复 keyword_scout 生成的 JSONL 文件中错误的 display_name"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

TARGET_BROKEN_NAME = "行吟信息科技（上海）有限公司"


def resolve_input_path(argv: Optional[List[str]] = None, reports_dir: str = "reports") -> Optional[Path]:
    argv = argv if argv is not None else sys.argv[1:]
    if argv:
        return Path(argv[0])

    files = sorted(Path(reports_dir).glob("keyword_scout_母婴室_*.jsonl"))
    if files:
        return files[-1]
    return None


def infer_display_name(record: Dict[str, Any]) -> str:
    profile = record.get("profile", {}) or {}
    bio = str(profile.get("bio", "") or "")
    account_id = str(record.get("account_id", "") or "")

    new_name = ""
    if bio:
        parts = bio.split("IP属地：")
        if len(parts) > 1:
            after_ip = parts[1].strip()
            ip_location_match = after_ip.split()
            if len(ip_location_match) > 1:
                new_name = " ".join(ip_location_match[1:]).strip()[:30]

    if not new_name and account_id:
        new_name = f"用户_{account_id[:10]}"
    if not new_name:
        new_name = f"用户_{record.get('index', 0)}"
    return new_name


def fix_record(record: Dict[str, Any]) -> tuple[Dict[str, Any], bool]:
    profile = record.get("profile", {}) or {}
    old_name = str(profile.get("display_name", "") or "")
    if old_name != TARGET_BROKEN_NAME:
        return record, False

    fixed_record = dict(record)
    fixed_profile = dict(profile)
    fixed_profile["display_name"] = infer_display_name(record)
    fixed_record["profile"] = fixed_profile
    return fixed_record, True


def load_jsonl(file_path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def write_jsonl(file_path: Path, records: Iterable[Dict[str, Any]]):
    with open(file_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def process_file(file_path: Path) -> tuple[Path, int, int]:
    data = load_jsonl(file_path)
    fixed_data: List[Dict[str, Any]] = []
    fixed_count = 0
    for record in data:
        fixed_record, changed = fix_record(record)
        if changed:
            fixed_count += 1
        fixed_data.append(fixed_record)

    output_path = file_path.with_suffix(".fixed.jsonl")
    write_jsonl(output_path, fixed_data)
    return output_path, len(fixed_data), fixed_count


def main(argv: Optional[List[str]] = None) -> int:
    file_path = resolve_input_path(argv)
    if file_path is None:
        print("未找到文件，请提供文件路径")
        return 1

    print(f"处理文件: {file_path}")
    output_path, total_count, fixed_count = process_file(file_path)
    print(f"\n修复完成！输出文件: {output_path}")
    print(f"共处理 {total_count} 条记录，修复 {fixed_count} 条异常名称")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
