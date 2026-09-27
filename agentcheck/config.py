"""Central settings, read from environment / .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
AGENTS_DIR = DATA_DIR / "agents"
SEED_DIR = DATA_DIR / "seed_agents"
AUDIT_DB = DATA_DIR / "audit.db"

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5")
# low / medium / high — medium keeps the demo responsive.
CLAUDE_EFFORT = os.getenv("CLAUDE_EFFORT", "medium")

# How many registry agents Layer 2 hands to the LLM judge.
TOP_K_CANDIDATES = int(os.getenv("TOP_K_CANDIDATES", "4"))

# Verdict thresholds (coverage %).
DUPLICATE_THRESHOLD = 90
HIGH_OVERLAP_THRESHOLD = 70
PARTIAL_THRESHOLD = 40

# A two-agent combination is only suggested if it beats the best single agent by this much.
COMBO_MIN_GAIN = 15
