from app.core.extract import FIELD_ORDER, NOT_FOUND

REQUIRED = {
    "study_certificate": {
        "text": {
            "rule:3.1": [
                "student_name", "university", "program", "study_form",
                "study_start", "study_end", "document_number", "issue_date",
            ],
        },
        "flag": {
            "rule:3.2": "signature_present",
            "rule:3.3": "seal_present",
        },
    },
    "academic_leave_application": {
        "text": {
            "rule:4.1": [
                "student_name", "group", "course", "leave_reason",
                "leave_start", "leave_end", "application_date",
            ],
        },
        "flag": {
            "rule:4.2": "signature_present",
        },
    },
    "internship": {
        "text": {
            "rule:5.1": [
                "student_name", "organization", "internship_start",
                "internship_end", "supervisor_name", "grade",
                "document_number", "issue_date",
            ],
        },
        "flag": {
            "rule:5.2": "signature_present",
            "rule:5.3": "seal_present",
        },
    },
}

def validate(fields: dict, doc_type: str) -> dict:
    cfg = REQUIRED[doc_type]
    missing = set[str] = set()
    sources = set[str] = set()

    for rule, keys in cfg["rule"].items():
        for k in keys:
            if fields.get(k) == NOT_FOUND:
                missing.add(k)
                sources.add(rule)

    for rule, flag in cfg["flag"].items():
        if not fields.get(flag, False):
            missing.add(flag)
            sources.add(rule)

    order = FIELD_ORDER[doc_type]
    missing_sorted = [k for k in order if k in missing]

    if missing_sorted:
        return {
            "status": "missing_fields",
            "missing_fields": missing_sorted,
            "sources": sorted(sources),
        }

    all_sources = sorted(set(cfg["text"]) | set(cfg["flag"]))
    return {
        "status": "document_ok",
        "missing_fields": [],
        "sources": all_sources,
    }
