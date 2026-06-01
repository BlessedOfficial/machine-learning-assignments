"""30 minimal AI.Inc internal documents for RAG (assignment corpus)."""

DOCS: list[tuple[str, str]] = []


def d(filename: str, body: str) -> None:
    DOCS.append((filename, body.strip() + "\n"))


# HR (6)
d(
    "pto-and-leave-policy.md",
    """
# PTO and Leave — AI.Inc
**Policy ID:** HR-PTO-2024-01

- Full-time employees: **20 PTO days** per year; max carryover **5 days** (forfeit March 31).
- Part-time (20–29 hrs/week): **12 PTO days**.
- Request in **WorkDay**; 10+ business days notice for leave over 3 days.
- Sick leave: **10 days** per year, separate from PTO.
- Contact: **peopleops@ai.inc**
""",
)

d(
    "remote-work-policy.md",
    """
# Remote Work — AI.Inc
**Policy ID:** HR-RW-2024-02

- Default: up to **3 days** remote per week for Remote-Eligible roles.
- Fully remote requires Director + HR approval.
- Core hours: **10:00 AM–3:00 PM** local time; VPN required.
- Contact: **remote@ai.inc**
""",
)

d(
    "benefits-overview.md",
    """
# Benefits Overview — AI.Inc
**Policy ID:** HR-BEN-2024-01

- Medical/dental/vision via **BluePeak Health**; company pays **85%** of employee premium.
- **401(k)** with **4% match** after 90 days.
- Wellness stipend: **$600/year** via Benify.
- Open enrollment: **November 1–15** annually.
- Contact: **benefits@ai.inc**
""",
)

d(
    "parental-leave-policy.md",
    """
# Parental Leave — AI.Inc
**Policy ID:** HR-PL-2024-01

- Birth parent: **12 weeks paid** at 100% salary.
- Non-birth / adoptive / foster: **8 weeks paid**.
- Contact: **parental-leave@ai.inc**
""",
)

d(
    "code-of-conduct.md",
    """
# Code of Conduct — AI.Inc
**Policy ID:** HR-COC-2023-11

- Treat colleagues, customers, and partners with respect.
- Protect confidential information; report issues to **ethics@ai.inc**.
- Contact: **peopleops@ai.inc**
""",
)

d(
    "employee-referral-program.md",
    """
# Employee Referrals — AI.Inc
**Policy ID:** HR-REF-2024-04

- Engineering referrals: **$3,000** after 90 days; other roles: **$1,500**.
- Submit via **Greenhouse** before candidate applies.
- Contact: **referrals@ai.inc**
""",
)

# IT (8)
d(
    "vpn-setup-guide.md",
    """
# VPN Setup — AI.Inc
**Document ID:** IT-VPN-001

- Install **AI.Inc SecureConnect** from Company Portal (Windows/macOS).
- Sign in with corporate email and **Okta Verify** MFA.
- Split tunnel: `*.ai.inc` and `10.0.0.0/8` only.
- Support: **vpn-help@ai.inc** | Slack **#it-vpn**
""",
)

d(
    "password-and-mfa-policy.md",
    """
# Password and MFA — AI.Inc
**Policy ID:** IT-SEC-2024-01

- Passwords: min **14 characters** with complexity rules.
- **Okta Verify** MFA required for all staff.
- Lockout after **5 failed attempts** for 30 minutes.
- Contact: **identity@ai.inc**
""",
)

d(
    "laptop-equipment-policy.md",
    """
# Laptops and Equipment — AI.Inc
**Policy ID:** IT-EQP-2024-02

- Standard issue: company laptop; refresh every **36 months**.
- Requests via ServiceNow catalog **IT-HW**.
- Report loss within **24 hours**: **helpdesk@ai.inc**
""",
)

d(
    "it-incident-reporting.md",
    """
# IT Incidents — AI.Inc
**Document ID:** IT-INC-002

- **SEV1**: company-wide outage — call **+1-800-555-0142**.
- **SEV2**: major team impact — Slack **#it-incidents**.
- **SEV3**: individual issues — ServiceNow ticket.
- Contact: **helpdesk@ai.inc**
""",
)

d(
    "okta-access-recovery.md",
    """
# Okta Recovery — AI.Inc
**Document ID:** IT-ID-003

- Reset password at **okta.ai.inc**.
- Lost MFA: contact Helpdesk Mon–Fri **9 AM–6 PM ET**.
- Contact: **identity@ai.inc**
""",
)

d(
    "servicenow-request-guide.md",
    """
# ServiceNow Requests — AI.Inc
**Document ID:** IT-SN-001

- **IT-HW**: hardware | **IT-ACC**: app access | **IT-VPN**: VPN exceptions.
- SLA: access **2 business days**; hardware ship **5 business days** (US).
- Contact: **helpdesk@ai.inc**
""",
)

d(
    "acceptable-use-policy-it.md",
    """
# IT Acceptable Use — AI.Inc
**Policy ID:** IT-AUP-2023-08

- Company systems for business use; limited personal use allowed.
- Prohibited: illegal activity, credential sharing, bypassing security.
- Contact: **it-policy@ai.inc**
""",
)

# Security (4)
d(
    "data-classification-policy.md",
    """
# Data Classification — AI.Inc
**Policy ID:** SEC-DATA-2024-01

- Levels: **Public**, **Internal**, **Confidential**, **Restricted**.
- Restricted data: encrypt in transit and at rest; no personal email.
- Contact: **grc@ai.inc**
""",
)

d(
    "security-incident-response.md",
    """
# Security Incidents — AI.Inc
**Policy ID:** SEC-IR-2024-01

- Report phishing, malware, or data concerns: **security-incident@ai.inc**.
- Triage within **1 hour** (business hours).
- Contact: **secops@ai.inc**
""",
)

d(
    "phishing-awareness.md",
    """
# Phishing — AI.Inc
**Document ID:** SEC-PHISH-001

- Use Outlook **Report Phishing** button.
- AI.Inc will never ask for passwords or MFA codes by email.
- Contact: **phishing@ai.inc**
""",
)

d(
    "clean-desk-policy.md",
    """
# Clean Desk — AI.Inc
**Policy ID:** SEC-DESK-2023-07

- Lock screen after **5 minutes** idle.
- Secure confidential papers when away from desk.
""",
)

# Onboarding (4)
d(
    "first-day-checklist.md",
    """
# First Day — AI.Inc
**Document ID:** ONB-001

- Badge pickup **9:00 AM**; orientation **10:00 AM–12:00 PM**.
- Complete **Security Training 101** by day 5.
- Set up Okta, VPN, and email in week 1.
- Contact: **onboarding@ai.inc**
""",
)

d(
    "access-provisioning-sla.md",
    """
# Access Provisioning — AI.Inc
**Document ID:** ONB-004

- Okta/email: **4 hours** | GitHub: **1 business day** | AWS sandbox: **2 business days**.
- Production access: **5 business days** + security review.
""",
)

d(
    "org-structure-overview.md",
    """
# Organization — AI.Inc
**Document ID:** ONB-003

- CEO: Alex Morgan | CTO: Priya Nair | CPO: Jordan Lee | CFO: Sam Okonkwo.
- Divisions: Engineering, Product & Design, Go-to-Market, G&A.
- Headcount: ~**850** employees; HQ **San Francisco**.
""",
)

# Engineering (4)
d(
    "ai-inc-product-overview.md",
    """
# Products — AI.Inc (Internal)
**Document ID:** PROD-001

- **NexusAI Studio**: LLM workflow builder.
- **GuardRail Hub**: policy/safety layer for deployments.
- **InsightLake**: usage and quality analytics.
""",
)

d(
    "github-enterprise-usage.md",
    """
# GitHub Enterprise — AI.Inc
**Document ID:** ENG-GH-001

- Org: **github.com/ai-inc**; all production code must live here.
- `main` requires PR, CI, and two approvals for production repos.
""",
)

d(
    "on-call-rotation.md",
    """
# On-Call — AI.Inc Engineering
**Document ID:** ENG-ONCALL-001

- **24/7** coverage for Tier-1 production services.
- **One week** rotations; stipend **$500/week**.
- Contact: **oncall@ai.inc**
""",
)

d(
    "code-review-policy.md",
    """
# Code Review — AI.Inc
**Document ID:** ENG-CR-001

- **Two approvals** for production; **one** for internal tools.
- Target response: **1 business day**.
""",
)

# Finance (4)
d(
    "expense-reimbursement.md",
    """
# Expenses — AI.Inc
**Policy ID:** FIN-EXP-2024-01

- Submit in **Concur** within **30 days**; receipt required over **$25**.
- Manager approval under **$500**; Finance over **$500**.
- Contact: **expenses@ai.inc**
""",
)

d(
    "business-travel-policy.md",
    """
# Business Travel — AI.Inc
**Policy ID:** FIN-TRV-2024-02

- Book via **Concur Travel**; economy under **6 hours** flights.
- US meal per diem: **$75/day**.
- Contact: **travel@ai.inc**
""",
)

# Legal & workplace (4)
d(
    "confidentiality-nda-policy.md",
    """
# Confidentiality — AI.Inc
**Policy ID:** LEG-NDA-2023-09

- Protect **Confidential** and **Restricted** data during and after employment.
- External NDAs via Legal / **Ironclad**.
""",
)

d(
    "whistleblower-hotline.md",
    """
# Ethics Hotline — AI.Inc
**Policy ID:** LEG-ETH-2023-12

- **+1-888-555-0199** (24/7) or **ethics.ai.inc/report**.
- No retaliation for good-faith reports.
""",
)

d(
    "office-hours-and-holidays.md",
    """
# Office and Holidays — AI.Inc
**Document ID:** FAC-001

- Offices open **8 AM–6 PM** local time.
- **11 US paid holidays** per year (see People Ops calendar).
- SF HQ: **500 Market Street, Floor 12–14**.
""",
)

d(
    "helpdesk-support-tiers.md",
    """
# Helpdesk — AI.Inc
**Document ID:** SUP-001

- Email: **helpdesk@ai.inc** | Phone: **+1-800-555-0100**.
- Hours: **24/7** for SEV1–2; general **7 AM–7 PM PT**.
- Self-service: **kb.ai.inc**
""",
)
