#!/usr/bin/env python3
"""Build editor/help_text.h from JBE_MANUAL.md.

The same single source (the manual) feeds both the printed PDF and the editor's
built-in F1 help, so they can never drift. This host tool turns the Markdown
into a flat, screen-wrapped, CP437-encoded plain-text version plus an anchor
table that maps a menu or item id to a line number, e.g.:

    "menu:File"        -> line 120
    "item:File/New"    -> line 126

The editor includes the generated header and the F1 router jumps to the anchor
for the current menu / highlighted item. Dependency: Python standard library
only. Run from the repository root:

    python3 tools/mkhelp.py        # JBE_MANUAL.md -> editor/help_text.h
"""
import os, re

TOOLS = os.path.dirname(os.path.abspath(__file__)) + "/"
ROOT  = os.path.abspath(os.path.join(TOOLS, "..")) + "/"
SRC   = ROOT + "JBE_MANUAL.md"
OUT   = ROOT + "editor/help_text.h"

WRAP   = 86                       # content width inside the 92-wide window
TITLES = {"File", "Edit", "View", "Search", "Macro", "Options", "Run"}

# Unicode -> CP437 (the editor font). Anything else becomes '?'.
U2CP = {
    "—": "-",        # em dash
    "·": "\xfa",     # middle dot ·
    "→": "\x1a",     # right arrow →
    "←": "\x1b",     # left arrow ←
    "↑": "\x18",     # up arrow ↑
    "↓": "\x19",     # down arrow ↓
    "─": "\xc4",     # box horizontal ─
    "…": "...",      # ellipsis …
}


def to_cp437(t):
    out = []
    for ch in t:
        if ord(ch) < 128:
            out.append(ch)
        elif ch in U2CP:
            out.append(U2CP[ch])
        else:
            out.append("?")
    return "".join(out)


def strip_inline(t):
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"\*\*([^*]+?)\*\*", r"\1", t)
    t = re.sub(r"(?<![\*\w])\*([^*]+?)\*(?![\*\w])", r"\1", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", t)
    return t


def wrap(t, width=WRAP):
    words = t.split()
    if not words:
        return [""]
    lines, cur = [], words[0]
    for w in words[1:]:
        if len(cur) + 1 + len(w) <= width:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def norm_label(s):
    """Shared with the F1 router in jbe.c: trim, drop a trailing '...'."""
    return re.sub(r"\.\.\.$", "", s.strip()).strip()


def is_table_sep(line):
    s = line.strip()
    return bool(s) and set(s) <= set("|:- ") and "-" in s


def cells(row):
    s = row.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


# ---- parse the manual into (text, heading) lines + anchors ----------------
out = []          # list of [text, heading_flag]
anchors = []      # list of (id, line_index)


def emit(text, head=0):
    out.append([text, head])


md = open(SRC, encoding="utf-8").read().split("\n")
cur_menu = None
i, n = 0, len(md)
while i < n:
    ln = md[i]
    s = ln.strip()

    if not s:
        emit("", 0); i += 1; continue

    if s in ("---", "***", "___"):
        emit("\xc4" * 40, 0); i += 1; continue          # a horizontal rule

    m = re.match(r"(#{1,6})\s+(.*)", s)
    if m:
        level = len(m.group(1))
        title = strip_inline(m.group(2)).strip()
        mm = re.match(r"(.+) menu$", title)
        if level == 2 and mm and mm.group(1) in TITLES:
            cur_menu = mm.group(1)
            anchors.append(("menu:" + cur_menu, len(out)))
        elif level == 2:
            cur_menu = None                              # left the menu chapters
        elif level == 3 and cur_menu:
            label = norm_label(title.split(" - ")[0].split("—")[0])
            anchors.append(("item:%s/%s" % (cur_menu, label), len(out)))
        emit(to_cp437(title), 1)
        i += 1; continue

    if s.startswith("|") and i + 1 < n and is_table_sep(md[i + 1]):
        head = cells(ln); i += 2; body = []
        while i < n and md[i].strip().startswith("|"):
            body.append(cells(md[i])); i += 1
        rows = [head] + body
        ncol = len(head)
        wid = [max(len(strip_inline(r[c])) if c < len(r) else 0 for r in rows)
               for c in range(ncol)]
        def fmt(r):
            parts = [(strip_inline(r[c]) if c < len(r) else "").ljust(wid[c])
                     for c in range(ncol)]
            return to_cp437("  ".join(parts).rstrip())
        emit(fmt(head), 0)
        emit("  ".join("\xc4" * wid[c] for c in range(ncol)), 0)   # already CP437
        for r in body:
            emit(fmt(r), 0)
        continue

    if re.match(r"[-*]\s+", s):
        while i < n and re.match(r"[-*]\s+", md[i].strip()):
            item = strip_inline(re.sub(r"^[-*]\s+", "", md[i].strip()))
            wl = wrap(to_cp437(item), WRAP - 4)
            emit("  \xfa " + wl[0], 0)                   # · bullet
            for extra in wl[1:]:
                emit("    " + extra, 0)
            i += 1
        continue

    para = []
    while (i < n and md[i].strip()
           and not re.match(r"(#{1,6}\s|[-*]\s|\|)", md[i].strip())
           and md[i].strip() not in ("---", "***", "___")):
        para.append(md[i].strip()); i += 1
    for wl in wrap(to_cp437(strip_inline(" ".join(para)))):
        emit(wl, 0)


# ---- emit the C header ----------------------------------------------------
def cstr(t):
    r = []
    for ch in t:
        b = ord(ch)
        if b == 0x22:
            r.append('\\"')
        elif b == 0x5c:
            r.append("\\\\")
        elif 0x20 <= b <= 0x7e:
            r.append(ch)
        else:
            r.append("\\%03o" % b)       # 3-digit octal: unambiguous
    return "".join(r)


with open(OUT, "w") as f:
    f.write("/* GENERATED by tools/mkhelp.py from JBE_MANUAL.md -- do not edit. */\n")
    f.write("#ifndef JBE_HELP_TEXT_H\n#define JBE_HELP_TEXT_H\n\n")
    f.write("typedef struct { const char *text; unsigned char heading; } help_line_t;\n")
    f.write("static const help_line_t HELP_LINES[] = {\n")
    for text, head in out:
        f.write('    { "%s", %d },\n' % (cstr(text), head))
    f.write("};\n")
    f.write("static const int HELP_NLINES = (int)(sizeof HELP_LINES / sizeof HELP_LINES[0]);\n\n")
    f.write("typedef struct { const char *id; int line; } help_anchor_t;\n")
    f.write("static const help_anchor_t HELP_ANCHORS[] = {\n")
    for aid, line in anchors:
        f.write('    { "%s", %d },\n' % (cstr(aid), line))
    f.write("    { 0, 0 }\n};\n\n")
    f.write("#endif\n")

print("wrote %s: %d lines, %d anchors" % (OUT, len(out), len(anchors)))
