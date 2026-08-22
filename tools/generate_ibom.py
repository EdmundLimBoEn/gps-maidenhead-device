#!/usr/bin/env python3
"""Generate a self-contained searchable assembly BOM for review."""

# SPDX-License-Identifier: CC-BY-SA-4.0

from __future__ import annotations

import argparse
import csv
import html
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bom", type=Path)
    parser.add_argument("placement", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.bom.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = list(reader)

    headings = "".join(f"<th>{html.escape(field)}</th>" for field in fields)
    body = "".join(
        f'<tr data-ref="{html.escape(row.get("Designator", ""))}">'
        + "".join(f"<td>{html.escape(row.get(field, ''))}</td>" for field in fields)
        + "</tr>"
        for row in rows
    )
    with args.placement.open(newline="", encoding="utf-8-sig") as handle:
        placements = [
            {
                "ref": row["Designator"],
                "x": float(row["Mid X"]),
                "y": -float(row["Mid Y"]),
                "side": row["Layer"].lower(),
            }
            for row in csv.DictReader(handle)
        ]
    placement_json = json.dumps(placements, separators=(",", ":")).replace("</", "<\\/")
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Pocket Locator assembly BOM</title>
<style>body{{font:14px system-ui;margin:2rem}}input{{padding:.5rem;width:28rem;max-width:90%}}
table{{border-collapse:collapse;margin-top:1rem}}th,td{{border:1px solid #bbb;padding:.35rem;vertical-align:top}}
th{{position:sticky;top:0;background:#eee}}tr[hidden]{{display:none}}tr.selected{{background:#ffec99}}
#board{{position:relative;aspect-ratio:81/37;max-width:70rem;border:2px solid #333;background:#173b2c;margin-top:1rem}}
.dot{{position:absolute;width:9px;height:9px;border:1px solid #111;border-radius:50%;background:#66d9ef;transform:translate(-50%,-50%);cursor:pointer}}
.dot.bottom{{background:#f78c6c}}.dot.selected{{width:17px;height:17px;background:#ffe66d;z-index:2}}</style>
</head><body><h1>Pocket Locator interactive assembly BOM</h1>
<p>Search or select a row/reference to cross-probe its board position. Cyan is top; coral is bottom.</p>
<label>Filter <input id="filter" type="search" autocomplete="off"></label>
<table><thead><tr>{headings}</tr></thead><tbody>{body}</tbody></table>
<h2>Board placement map</h2><div id="board" role="img" aria-label="Interactive 81 by 37 millimetre PCB placement map"></div>
<script>const placements={placement_json};const board=document.querySelector('#board');
for(const p of placements){{const d=document.createElement('button');d.className='dot '+p.side;d.dataset.ref=p.ref;
d.title=p.ref+' ('+p.side+')';d.style.left=(p.x/81*100)+'%';d.style.top=(p.y/37*100)+'%';board.append(d);}}
function select(ref){{for(const e of document.querySelectorAll('[data-ref]'))e.classList.toggle('selected',e.dataset.ref===ref);
const row=document.querySelector('tbody tr[data-ref="'+CSS.escape(ref)+'"]');if(row)row.scrollIntoView({{block:'center'}});}}
document.addEventListener('click',e=>{{const target=e.target.closest('[data-ref]');if(target)select(target.dataset.ref);}});
const f=document.querySelector('#filter');f.addEventListener('input',()=>{{const q=f.value.toLowerCase();
for(const r of document.querySelectorAll('tbody tr'))r.hidden=!r.textContent.toLowerCase().includes(q);}});</script>
</body></html>
"""
    args.output.write_text(document, encoding="utf-8")


if __name__ == "__main__":
    main()
