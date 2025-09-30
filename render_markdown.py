#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Optional

def fmt_bytes(n: int) -> str:
    return f"{int(n):,} bytes"

def fmt_with_pct(used: int, pct: Optional[float], precision: int) -> str:
    if isinstance(pct, (int, float)):
        return f"{int(used):,} bytes ({pct:.{precision}f}%)"
    return f"{int(used):,} bytes"

def compute_pct(used: int, total: int, precision: int) -> Optional[float]:
    try:
        if total and total > 0:
            return round((used / total) * 100.0, precision)
    except Exception:
        pass
    return None

def fmt_delta(delta: int, delta_pct: Optional[float], precision: int) -> str:
    arrow = ""
    if delta > 0:
        arrow = "🔺 "
    elif delta < 0:
        arrow = "⬇️ " # 🟢⬇️ "
    pct_part = ""
    if isinstance(delta_pct, (int, float)):
        sign = "+" if delta_pct > 0 else ""
        pct_part = f" ({sign}{delta_pct:.{precision}f}%)"
    sign_bytes = "+" if delta > 0 else ""
    return f"{arrow}{sign_bytes}{delta:,} bytes{pct_part}"

def main():
    ap = argparse.ArgumentParser(description="Render markdown size table for ESP-IDF app")
    ap.add_argument("--app-name", required=True)
    ap.add_argument("--head-json", required=True, help="Path to head size.json")
    ap.add_argument("--base-json", required=True, help="Path to base size.json")
    ap.add_argument("--flash-total-override", type=int, default=0)
    ap.add_argument("--precision", type=int, default=2)
    args = ap.parse_args()

    head = json.loads(Path(args.head_json).read_text())
    base = json.loads(Path(args.base_json).read_text())

    # Extract used values
    def used(d, k):
        return int(d.get(k, 0))

    pr = {
        'flash': used(head, 'flash'),
        'dram': used(head, 'dram'),
        'iram': used(head, 'iram'),
        'ram': used(head, 'ram'),
        'flash_total': int(head.get('flash_total', 0)),
        'dram_total': int(head.get('dram_total', 0)),
        'iram_total': int(head.get('iram_total', 0)),
    }
    basev = {
        'flash': used(base, 'flash'),
        'dram': used(base, 'dram'),
        'iram': used(base, 'iram'),
        'ram': used(base, 'ram'),
        'flash_total': int(base.get('flash_total', 0)),
        'dram_total': int(base.get('dram_total', 0)),
        'iram_total': int(base.get('iram_total', 0)),
    }

    # Apply optional FLASH total override for percent display
    flash_total_override = int(args.flash_total_override) if args.flash_total_override and args.flash_total_override > 0 else 0
    if flash_total_override > 0:
        pr['flash_total'] = flash_total_override
        basev['flash_total'] = flash_total_override

    # DRAM/IRAM pct compute if totals present and missing
    # Percentages will be computed on the fly from used/total

    def fmt_row(label: str, key: str, show_pct: bool) -> str:
        # compute percent for base/pr from used/total if totals present
        base_pct = None
        pr_pct = None
        if show_pct:
            bt = int(basev.get(f"{key}_total", 0)) if key != 'flash' else int(basev.get('flash_total', 0))
            pt = int(pr.get(f"{key}_total", 0)) if key != 'flash' else int(pr.get('flash_total', 0))
            if bt > 0:
                base_pct = compute_pct(basev[key], bt, args.precision)
            if pt > 0:
                pr_pct = compute_pct(pr[key], pt, args.precision)
        base_cell = fmt_with_pct(basev[key], base_pct, args.precision) if show_pct else fmt_bytes(basev[key])
        pr_cell = fmt_with_pct(pr[key], pr_pct, args.precision) if show_pct else fmt_bytes(pr[key])
        delta = pr[key] - basev[key]
        delta_pct = None
        if show_pct:
            if isinstance(base_pct, (int, float)) and isinstance(pr_pct, (int, float)):
                delta_pct = round(pr_pct - base_pct, args.precision)
        elif key == 'ram':
            # Try to compute RAM percentage based on summed DRAM+IRAM totals
            base_total = int(basev.get('dram_total', 0)) + int(basev.get('iram_total', 0))
            pr_total = int(pr.get('dram_total', 0)) + int(pr.get('iram_total', 0))
            if base_total > 0 and pr_total > 0:
                bp = compute_pct(basev['ram'], base_total, args.precision)
                pp = compute_pct(pr['ram'], pr_total, args.precision)
                if bp is not None and pp is not None:
                    delta_pct = round(pp - bp, args.precision)
        return f"| {label} | {base_cell} | {pr_cell} | {fmt_delta(delta, delta_pct, args.precision)} |"

    rows = []
    rows.append(fmt_row('FLASH', 'flash', True))
    rows.append(fmt_row('DRAM', 'dram', True))
    rows.append(fmt_row('IRAM', 'iram', True))
    rows.append(fmt_row('RAM (DRAM+IRAM)', 'ram', False))

    # Totals row removed per request

    md = [
        f"### ESP-IDF Size Report for '{args.app_name}'",
        "",
        "| Metric | Base | PR | Delta |",
        "|---|---:|---:|---:|",
        *rows,
        "",
        "<sub>FLASH uses app .bin size or json2 flash sum. RAM sums DRAM+IRAM via idf_size. Percentages shown when totals are available.</sub>",
        "",
        f"<!-- esp-idf-size-delta:{args.app_name} -->",
    ]
    print("\n".join(md))

if __name__ == "__main__":
    main()
