"""Sample inputs so each seed agent can be run live in the demo (all fictional)."""

SAMPLES = {
    "email_summarizer": """From: Priya Shah
To: Dev Team
Subject: Release 4.2 - final checks

Hi all, QA found two blockers in the billing module (BUG-311, BUG-314). Arjun, can you fix both by Thursday?
Also, Maria please update the release notes before Friday's go/no-go call at 3pm.

---
From: Arjun Rao
Re: Release 4.2 - final checks

BUG-311 is fixed. BUG-314 needs a DB migration, I will need Kevin's review. Should be done Thursday EOD.

---
From: Kevin Li
Re: Release 4.2 - final checks

Happy to review the migration Thursday morning. Let's keep the go/no-go on Friday.""",
    "invoice_extractor": """ACME Office Supplies Ltd.
Invoice No: INV-2026-0457
Invoice Date: 2026-09-01     Due Date: 2026-10-01
Bill To: Contoso Demo Corp

Item                    Qty   Unit Price   Amount
Ergonomic chair          4      $250.00    $1,000.00
Standing desk            2      $480.00      $960.00
Monitor arm              6       $45.00      $270.00

Subtotal: $2,230.00
Tax (8%): $178.40
TOTAL DUE: USD 2,408.40""",
    "sentiment_analyzer": """1. The new portal is so much faster, booking an appointment took under a minute!
2. Support took three days to answer a simple billing question. Not happy.
3. It works. Nothing special.""",
    "translator": """Translate to English:
El producto llegó a tiempo y funciona perfectamente. El servicio al cliente fue muy amable, aunque la aplicación móvil todavía es un poco lenta.""",
    "meeting_notes_generator": """[10:00] Sam: Let's decide on the vendor for the analytics dashboard.
[10:02] Lee: Vendor B is 20% cheaper but lacks SSO.
[10:04] Sam: SSO is mandatory for us. Let's go with Vendor A.
[10:05] Lee: OK. I'll send the contract to legal by Wednesday.
[10:07] Priya: Do we know the rollout date?
[10:08] Sam: Not yet - Priya, can you draft a rollout plan by next Monday?""",
    "sql_query_builder": """Schema:
patients(id, name, birth_date, state)
appointments(id, patient_id, provider_id, appt_date, status)
providers(id, name, specialty)

Question: How many completed appointments did each cardiology provider have in August 2026?""",
    "resume_screener": """JOB DESCRIPTION: Senior Python Developer - 5+ years Python, FastAPI or Django, PostgreSQL, AWS, experience with CI/CD. Nice to have: healthcare data (HL7/FHIR).

RESUME: Jordan K. - Software Engineer, 6 years.
- Built REST APIs with Django and FastAPI serving 2M requests/day
- PostgreSQL schema design and query tuning
- Deployed services on Azure with GitHub Actions
- Integrated HL7 feeds for a lab-results project""",
    "clinical_note_summarizer": """DISCHARGE SUMMARY (fictional patient)
Pt: 67 y/o male admitted with community-acquired pneumonia. PMH: type 2 diabetes, hypertension.
Allergies: penicillin (rash).
Hospital course: treated with IV ceftriaxone + azithromycin, transitioned to oral cefpodoxime. O2 weaned to room air day 3.
Discharge meds: cefpodoxime 200mg BID x5 days, metformin 1000mg BID, lisinopril 10mg daily.
Plan: follow up with PCP in 1 week, repeat chest X-ray in 6 weeks, monitor blood glucose.""",
}
