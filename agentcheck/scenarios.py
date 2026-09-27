"""The demo scenarios, in presentation order."""

from agentcheck.models import AgentRequest, Verdict

SCENARIOS = [
    {
        "title": "1. Exact duplicate",
        "shows": "The basic case works",
        "expected": Verdict.DUPLICATE,
        "request": AgentRequest(
            name="Email Thread Summary Agent",
            description="Summarize my email threads and list the action items with owners.",
            input_types=["email thread"],
            output_types=["summary", "action items"],
            domain="productivity / communication",
        ),
    },
    {
        "title": "2. Same job, different words",
        "shows": "Catches meaning, not just keywords",
        "expected": Verdict.DUPLICATE,
        "request": AgentRequest(
            name="Inbox Digest Bot",
            description="Gives me a daily gist of what's in my mail and what I need to do about it.",
            input_types=["mail messages"],
            output_types=["daily digest"],
            domain="productivity",
        ),
    },
    {
        "title": "3. The 80% case",
        "shows": "Coverage breakdown + the Extend option",
        "expected": Verdict.HIGH_OVERLAP,
        "request": AgentRequest(
            name="Invoice to SAP Agent",
            description="Read invoice PDFs, extract vendor, invoice number, dates, total amount and line items as JSON, then push that data into SAP.",
            input_types=["invoice PDF"],
            output_types=["JSON", "SAP posting"],
            domain="finance / accounts payable",
        ),
    },
    {
        "title": "4. Two agents together",
        "shows": "Suggests combining existing agents",
        "expected": Verdict.PARTIAL,
        "request": AgentRequest(
            name="Spanish Review Sentiment Agent",
            description="Translate Spanish customer reviews into English and tell me whether each one is positive, neutral or negative.",
            input_types=["Spanish customer reviews"],
            output_types=["English translation", "sentiment label"],
            domain="customer experience",
        ),
    },
    {
        "title": "5. Looks similar but isn't",
        "shows": "Not fooled by the shared word 'summarize'",
        "expected": Verdict.PARTIAL,
        "request": AgentRequest(
            name="Prior Auth Record Summarizer",
            description="Summarize patient discharge summaries into diagnoses, procedures and medical-necessity evidence for a prior-authorization review.",
            input_types=["discharge summary", "clinical notes"],
            output_types=["prior-auth evidence summary"],
            domain="healthcare / utilization management",
        ),
    },
    {
        "title": "6. Truly new",
        "shows": "Doesn't block genuinely new agents",
        "expected": Verdict.UNIQUE,
        "request": AgentRequest(
            name="Jira Sprint Health Reporter",
            description="Generate a weekly sprint health report from Jira: velocity, burndown, blocked tickets and carry-over risk.",
            input_types=["Jira sprint data"],
            output_types=["weekly sprint report"],
            domain="engineering / project management",
        ),
    },
    {
        "title": "7. Override with a reason",
        "shows": "Governance: 'Create anyway' needs a justification",
        "expected": Verdict.DUPLICATE,
        "request": AgentRequest(
            name="Outlook Email Summarizer",
            description="Summarize email threads and list action items, directly inside Outlook.",
            input_types=["email thread"],
            output_types=["summary", "action items"],
            domain="productivity / communication",
        ),
    },
    {
        "title": "8. Registry learns (run after #6)",
        "shows": "Newly added agents are protected too",
        "expected": Verdict.DUPLICATE,
        "request": AgentRequest(
            name="Sprint Status Summary",
            description="Every week, read our Jira sprint and report velocity, burndown, what's blocked and what will carry over.",
            input_types=["Jira sprint data"],
            output_types=["sprint status report"],
            domain="engineering / project management",
        ),
    },
]
