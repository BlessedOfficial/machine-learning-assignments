"""Detect questions outside the AI.Inc assistant scope."""

import re

# Legitimate AI.Inc workplace topics — do not block general policy questions.
_AI_INC_WORKPLACE = re.compile(
    r"\b(?:"
    r"ai\.inc|ai inc|company policy|our policy|internal policy|"
    r"pto|leave policy|benefits|vpn|okta|workday|servicenow|onboarding|"
    r"remote work|expense|reimbursement|code of conduct|referral|"
    r"parental leave|open enrollment|401\s*\(?k\)?|hr policy|it policy|"
    r"security policy|on-call|github|helpdesk"
    r")\b",
    re.IGNORECASE,
)

_HR_CONFIDENTIAL = re.compile(
    r"\b(?:"
    r"(?:another|other|coworker'?s?|colleague'?s?|someone else'?s?|"
    r"employee'?s?|my manager'?s?|my teammate'?s?)\s+"
    r"(?:[\w'-]+\s+){0,2}?"
    r"(?:salary|compensation|pay|bonus|pto balance|leave balance|"
    r"performance review|rating|disciplinary|write-?up|medical record|"
    r"health record|ssn|social security)|"
    r"(?:salary|compensation|pay grade)\s+(?:of|for)\s+[A-Z][a-z]+|"
    r"who (?:earns|makes|gets paid) (?:the )?most|"
    r"list (?:all )?employee salaries|"
    r"(?:export|dump|list|give me) (?:all )?employee "
    r"(?:emails?|phone numbers?|contact (?:info|details|data))|"
    r"employee (?:emails?|phone numbers?) (?:from|in) (?:the )?"
    r"(?:internal )?(?:directory|database|hr system)|"
    r"access (?:to )?(?:someone else'?s?|another employee'?s?) "
    r"(?:hr|personnel|payroll) (?:file|record|data)"
    r")\b",
    re.IGNORECASE,
)

_MEDICAL_PERSONAL = re.compile(
    r"\b(?:"
    r"diagnose|diagnosis|my symptoms|symptoms (?:of|for|mean)|"
    r"do i have (?:the )?(?:flu|covid|cancer|diabetes|appendicitis)|"
    r"should i take (?:this )?(?:medication|medicine|drug)|"
    r"what (?:dosage|dose)|treatment for my|"
    r"am i (?:sick|pregnant)|is it safe for me to (?:take|use)|"
    r"medical advice|doctor (?:for|about) my"
    r")\b",
    re.IGNORECASE,
)

_MEDICAL_POLICY = re.compile(
    r"\b(?:"
    r"benefits|health plan|medical plan|insurance coverage|"
    r"company medical|wellness stipend|open enrollment|"
    r"parental leave|sick leave policy|bluepeak"
    r")\b",
    re.IGNORECASE,
)

_LEGAL_ADVICE = re.compile(
    r"\b(?:"
    r"legal advice|should i sue|do i need a lawyer|"
    r"is it illegal for me (?:to|personally)|"
    r"can i sue (?:the company|ai\.inc|my employer)|"
    r"contract law (?:for|regarding) my|"
    r"will i go to jail|criminal liability (?:for me|personally)"
    r")\b",
    re.IGNORECASE,
)

_LEGAL_POLICY = re.compile(
    r"\b(?:"
    r"policy|nda|confidentiality|compliance|ethics hotline|"
    r"whistleblower|code of conduct|legal policy"
    r")\b",
    re.IGNORECASE,
)

_GENERAL_KNOWLEDGE = re.compile(
    r"\b(?:"
    r"capital of (?!our)|who won (?:the )?(?:world cup|super bowl|election)|"
    r"weather in|recipe for|translate (?:this|the following) to|"
    r"write (?:me )?(?:a poem|code for|an essay)|"
    r"stock price of (?!ai\.inc)|"
    r"tell me about (?:google|microsoft|apple|amazon|meta)\b"
    r")\b",
    re.IGNORECASE,
)

_PERSONAL_ADVICE = re.compile(
    r"\b(?:"
    r"relationship advice|dating advice|should i quit my job(?!\s+at ai)|"
    r"invest (?:in|my savings)|crypto advice|tax advice (?:for my|on my)|"
    r"mental health advice (?:for me|about my)"
    r")\b",
    re.IGNORECASE,
)


def detect_scope_violation(text: str) -> str | None:
    """
    Return a scope category if the question should be refused, else None.

    Categories: hr_confidential, medical_advice, legal_advice,
    general_knowledge, personal_advice
    """
    if _HR_CONFIDENTIAL.search(text):
        return "hr_confidential"

    if _MEDICAL_PERSONAL.search(text) and not _MEDICAL_POLICY.search(text):
        return "medical_advice"

    if _LEGAL_ADVICE.search(text) and not _LEGAL_POLICY.search(text):
        return "legal_advice"

    if _PERSONAL_ADVICE.search(text):
        return "personal_advice"

    if _GENERAL_KNOWLEDGE.search(text) and not _AI_INC_WORKPLACE.search(text):
        return "general_knowledge"

    return None
