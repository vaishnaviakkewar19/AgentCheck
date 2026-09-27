"""Generates docs/architecture.excalidraw for AgentCheck."""

import json
import random
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
random.seed(7)
elements = []
_n = 0


def _id(prefix):
    global _n
    _n += 1
    return f"{prefix}{_n}"


def _base(kind, x, y, w, h, **kw):
    e = {
        "id": _id(kind[:3]),
        "type": kind,
        "x": x, "y": y, "width": w, "height": h, "angle": 0,
        "strokeColor": kw.get("stroke", "#1e1e1e"),
        "backgroundColor": kw.get("bg", "transparent"),
        "fillStyle": "solid",
        "strokeWidth": kw.get("sw", 2),
        "strokeStyle": kw.get("style", "solid"),
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": kw.get("roundness", {"type": 3}),
        "seed": random.randint(1, 2**31),
        "version": 1,
        "versionNonce": random.randint(1, 2**31),
        "isDeleted": False,
        "boundElements": [],
        "updated": 1,
        "link": None,
        "locked": False,
    }
    elements.append(e)
    return e


def _text_el(x, y, text, size, container=None, align="center", color="#1e1e1e"):
    lines = text.split("\n")
    w = max(len(l) for l in lines) * size * 0.55
    h = len(lines) * size * 1.25
    if container:
        x = container["x"] + (container["width"] - w) / 2
        y = container["y"] + (container["height"] - h) / 2
    t = _base("text", x, y, w, h, stroke=color, roundness=None)
    t.update(
        text=text, originalText=text, fontSize=size, fontFamily=1,
        textAlign=align, verticalAlign="middle",
        containerId=container["id"] if container else None,
        lineHeight=1.25, autoResize=True,
    )
    if container:
        container["boundElements"].append({"id": t["id"], "type": "text"})
    return t


def box(x, y, w, h, label, bg="transparent", size=16, kind="rectangle", **kw):
    b = _base(kind, x, y, w, h, bg=bg, **kw)
    if label:
        _text_el(0, 0, label, size, container=b)
    return b


def text(x, y, s, size=16, color="#1e1e1e", align="left"):
    return _text_el(x, y, s, size, align=align, color=color)


def arrow(points, start=None, end=None, color="#1e1e1e", style="solid"):
    x0, y0 = points[0]
    rel = [[px - x0, py - y0] for px, py in points]
    xs, ys = [p[0] for p in rel], [p[1] for p in rel]
    a = _base("arrow", x0, y0, max(xs) - min(xs), max(ys) - min(ys), stroke=color, style=style,
              roundness={"type": 2})
    a.update(points=rel, lastCommittedPoint=None, startArrowhead=None, endArrowhead="arrow",
             startBinding=None, endBinding=None, elbowed=False)
    for key, el in (("startBinding", start), ("endBinding", end)):
        if el is not None:
            a[key] = {"elementId": el["id"], "focus": 0, "gap": 4}
            el["boundElements"].append({"id": a["id"], "type": "arrow"})
    return a


BLUE, YELLOW, ORANGE, GREEN, GRAY, PURPLE, PINK = (
    "#a5d8ff", "#ffec99", "#ffd8a8", "#b2f2bb", "#e9ecef", "#d0bfff", "#fcc2d7")

# ---------------- Title ----------------
text(40, 20, "AgentCheck - Architecture", 32)
text(40, 62, "Stops people from building an agent that already exists", 18, color="#868e96")

# ---------------- User ----------------
user = box(40, 120, 170, 80, "User\n(agent builder)", bg=PINK, kind="ellipse")

# ---------------- Streamlit UI ----------------
ui = box(260, 95, 1040, 150, None, style="dashed", sw=1)
text(275, 102, "Streamlit UI  ·  app.py", 18, color="#1971c2")
p_reg = box(280, 140, 230, 80, "Registry page\nbrowse agent cards", bg=BLUE)
p_create = box(530, 140, 230, 80, "Create Agent page\npropose a new agent", bg=BLUE)
p_run = box(780, 140, 230, 80, "Run Agent page\nrun / chain agents", bg=BLUE)
p_audit = box(1030, 140, 250, 80, "Audit Log page\nstats + decisions", bg=BLUE)
arrow([(212, 160), (276, 160)], user, p_reg)
text(206, 124, "uses", 14, color="#868e96")

# ---------------- Gatekeeper ----------------
gk = box(260, 295, 1040, 220, None, style="dashed", sw=1)
text(275, 302, "Gatekeeper  ·  agentcheck/gatekeeper.py", 18, color="#e8590c")
l1 = box(280, 345, 230, 140, "Layer 1\nDECOMPOSE (LLM)\n\nrequest -> 3-6 sub-tasks\n+ search keywords", bg=YELLOW, size=15)
l2 = box(530, 345, 230, 140, "Layer 2\nSHORTLIST\n(similarity.py)\n\nTF-IDF + synonyms\n-> top 4 agents", bg=YELLOW, size=15)
l3 = box(780, 345, 230, 140, "Layer 3\nJUDGE (LLM)\n\nper sub-task:\ncovered / partial / not\n+ domain & I/O check", bg=YELLOW, size=15)
sc = box(1030, 345, 250, 140, "SCORING (Python)\n\ncoverage =\n(covered + 0.5*partial)/n\nbest pair of agents\n-> verdict", bg=ORANGE, size=15)
arrow([(512, 415), (526, 415)], l1, l2)
arrow([(762, 415), (776, 415)], l2, l3)
arrow([(1012, 415), (1026, 415)], l3, sc)
arrow([(645, 222), (645, 291)], p_create, gk)
text(655, 250, "AgentRequest (name, description, inputs, outputs, domain)", 14, color="#868e96")

# ---------------- Claude ----------------
claude = box(1380, 340, 250, 130, "Claude API\n(Anthropic SDK · llm.py)\n\nstructured outputs\nclaude-opus-5", bg=PURPLE, size=15)
arrow([(1302, 405), (1376, 405)], gk, claude)
text(1306, 378, "L1 + L3", 14, color="#868e96")

# ---------------- Decision ----------------
dec = box(780, 565, 520, 70, "USER DECISION\nUse · Extend · Chain · Create anyway (with reason)", bg=GREEN, size=15)
arrow([(1155, 487), (1155, 561)], sc, dec)
text(1165, 515, "verdict + breakdown", 14, color="#868e96")

# ---------------- Storage + runtime ----------------
reg = box(280, 690, 340, 110, "Agent Registry  (registry.py)\ndata/agents/*.json manifests\nreset from data/seed_agents/", bg=GRAY, size=15)
run = box(660, 690, 300, 110, "Worker Agents  (runner.py)\n8 seed agents + new ones\nsystem prompt + input", bg=GRAY, size=15)
aud = box(1000, 690, 300, 110, "Audit Log  (audit.py)\nSQLite data/audit.db\nevery decision + reason", bg=GRAY, size=15)

arrow([(600, 489), (600, 686)], l2, reg)
text(608, 540, "reads\nmanifests", 14, color="#868e96")
arrow([(800, 637), (800, 655), (450, 655), (450, 686)], dec, reg)
text(470, 632, "register / extend", 14, color="#868e96")
arrow([(900, 637), (900, 686)], dec, run)
text(908, 650, "use / chain", 14, color="#868e96")
arrow([(1200, 637), (1200, 686)], dec, aud)
text(1208, 650, "log", 14, color="#868e96")
arrow([(658, 745), (624, 745)], run, reg)
arrow([(810, 802), (810, 850), (1680, 850), (1680, 405), (1634, 405)], run, claude)
text(1180, 856, "each agent run = 1 Claude call", 14, color="#868e96")

# ---------------- Legend ----------------
legend = box(1380, 520, 250, 280,
             "VERDICTS\n\n>= 90%   Duplicate\n70-89%   High overlap\npair >= 70%  Combine\n40-69%   Partial\n< 40%    Unique\n\nDomain mismatch\ncaps coverage at 30%",
             bg="#fff9db", size=15, style="dashed", sw=1)

doc = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
    "files": {},
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(doc, indent=2), encoding="utf-8")
print(f"wrote {OUT} with {len(elements)} elements")
