def extract_certification_status(data: dict) -> str:
    """
    Extract certification status from different asset schemas.

    Supports:

    {
        "certification_status": "PASS"
    }

    {
        "certification": {
            "status": "PASS"
        }
    }

    {
        "certification": "PASS"
    }
    """

    if "certification_status" in data:
        return str(data["certification_status"])

    certification = data.get("certification")

    if isinstance(certification, dict):
        return str(certification.get("status", "UNKNOWN"))

    if isinstance(certification, str):
        return certification

    return "UNKNOWN"