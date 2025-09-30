#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

def _extract_dram_iram_from_data(data):
    # Handle json2 layout: { "version": "1.x", "layout": [ {"name": "DIRAM"|"DRAM"|"IRAM", "used": N }, ... ] }
    if isinstance(data, dict) and isinstance(data.get('layout'), list):
        dram_used = None
        iram_used = None
        for seg in data['layout']:
            if not isinstance(seg, dict):
                continue
            name = str(seg.get('name', '')).lower()
            used = seg.get('used')
            if used is None:
                continue
            try:
                used = int(used)
            except Exception:
                continue
            if 'diram' in name or ('dram' in name and 'iram' not in name):
                dram_used = used
            elif 'iram' in name:
                iram_used = used
        if dram_used is not None and iram_used is not None:
            return dram_used, iram_used
        # If only one is present, still return what we have with 0 for the other
        if dram_used is not None or iram_used is not None:
            return int(dram_used or 0), int(iram_used or 0)

    # Prefer explicit dram/iram.used if present
    if isinstance(data, dict):
        dram = data.get('dram', {})
        iram = data.get('iram', {})
        if isinstance(dram, dict) and 'used' in dram and isinstance(iram, dict) and 'used' in iram:
            try:
                return int(dram['used']), int(iram['used'])
            except Exception:
                pass
        # Fallback: sum any keys that start with dram_/iram_ and have 'used'
        dram_sum = 0
        iram_sum = 0
        found_any = False
        for k, v in data.items():
            if isinstance(v, dict) and 'used' in v:
                if str(k).lower().startswith('dram'):
                    try:
                        dram_sum += int(v['used']); found_any = True
                    except Exception:
                        pass
                if str(k).lower().startswith('iram'):
                    try:
                        iram_sum += int(v['used']); found_any = True
                    except Exception:
                        pass
        if found_any:
            return dram_sum, iram_sum
        # Recurse into nested dicts/lists
        for v in data.values():
            if isinstance(v, (dict, list)):
                res = _extract_dram_iram_from_data(v)
                if res is not None:
                    return res
    elif isinstance(data, list):
        for item in data:
            res = _extract_dram_iram_from_data(item)
            if res is not None:
                return res
    return None

def _parse_size_totals_and_used(data):
    """Return dict with used/total for flash, dram (DIRAM), iram.

    Keys: flash_used, flash_total, dram_used, dram_total, iram_used, iram_total
    """
    result = {
        'flash_used': 0, 'flash_total': 0,
        'dram_used': 0,  'dram_total': 0,
        'iram_used': 0,  'iram_total': 0,
    }
    if isinstance(data, dict) and isinstance(data.get('layout'), list):
        flash_code = {'used': 0, 'total': 0}
        flash_data = {'used': 0, 'total': 0}
        diram = {'used': 0, 'total': 0}
        iram = {'used': 0, 'total': 0}
        for seg in data['layout']:
            if not isinstance(seg, dict):
                continue
            name = str(seg.get('name', '')).lower()
            used = seg.get('used')
            total = seg.get('total')
            try:
                used = int(used) if used is not None else 0
            except Exception:
                used = 0
            try:
                total = int(total) if total is not None else 0
            except Exception:
                total = 0
            if 'flash code' in name:
                flash_code['used'] = used; flash_code['total'] = total
            elif 'flash data' in name:
                flash_data['used'] = used; flash_data['total'] = total
            elif 'diram' in name or ('dram' in name and 'iram' not in name):
                diram['used'] = used; diram['total'] = total
            elif 'iram' in name:
                iram['used'] = used; iram['total'] = total
        result['flash_used'] = flash_code['used'] + flash_data['used']
        # If totals are unknown (0), sum will remain 0 which is acceptable
        result['flash_total'] = flash_code['total'] + flash_data['total']
        result['dram_used'] = diram['used']
        result['dram_total'] = diram['total']
        result['iram_used'] = iram['used']
        result['iram_total'] = iram['total']
        return result
    # Fallback for older JSON layout with dram/iram objects
    if isinstance(data, dict):
        dram = data.get('dram', {}) if isinstance(data.get('dram'), dict) else {}
        iram = data.get('iram', {}) if isinstance(data.get('iram'), dict) else {}
        def to_int(x):
            try:
                return int(x)
            except Exception:
                return 0
        result['dram_used'] = to_int(dram.get('used'))
        result['dram_total'] = to_int(dram.get('total') or dram.get('available'))
        result['iram_used'] = to_int(iram.get('used'))
        result['iram_total'] = to_int(iram.get('total') or iram.get('available'))
    return result


def main():
    p = argparse.ArgumentParser(description='Collect ESP-IDF app size metrics')
    p.add_argument('--in-file', default='idf_size.json', help='Path to read JSON input (from idf.py --format json/json2)')
    p.add_argument('--out-file', default='size.json', help='Path to write JSON output')
    p.add_argument('--flash-total-override', type=int, default=0,
                   help='Override total FLASH bytes for percentage (optional)')
    args = p.parse_args()

    result = {'flash': 0, 'dram': 0, 'iram': 0, 'ram': 0}

    size_data = json.loads(Path(args.in_file).read_text()) if Path(args.in_file).is_file() else None
    if size_data is not None:
        parsed = _parse_size_totals_and_used(size_data)
        dram = int(parsed['dram_used'])
        iram = int(parsed['iram_used'])
        flash_used = int(parsed['flash_used'])
        # If json has flash_used, prefer that over .bin size
        flash_val = flash_used if flash_used > 0 else int(flash)
        ram = dram + iram
        def pct(used: int, total: int):
            try:
                return round((used / total) * 100.0, 2) if total and total > 0 else None
            except Exception:
                return None
        flash_total = int(parsed['flash_total'])
        if args.flash_total_override and args.flash_total_override > 0:
            flash_total = int(args.flash_total_override)
        result = {
            'flash': flash_val,
            'dram': dram,
            'iram': iram,
            'ram': ram,
            'flash_total': flash_total,
            'dram_total': int(parsed['dram_total']),
            'iram_total': int(parsed['iram_total']),
        }
    Path(args.out_file).write_text(json.dumps(result))
    return 0

if __name__ == '__main__':
    sys.exit(main())
