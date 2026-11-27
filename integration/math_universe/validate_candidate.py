"""Shape-only validator for an inert comparison manifest, never authority."""
import re

OWNERS = frozenset(("Grid", "Math", "Terminan", "Unified System"))
FIELDS = frozenset(("schema", "repositories", "status",
                    "independentQualification", "executionAuthority",
                    "tradingAuthorized"))
HEX40 = re.compile(r"[0-9a-f]{40}")


def validate_candidate(value):
    """Accept only a decoded inert DTO; return None or raise ValueError.

    Decoding belongs to the shared codec boundary. This function does not
    authenticate Git objects, qualify a candidate or grant permissions.
    """
    if type(value) is not dict or any(type(k) is not str for k in value):
        raise ValueError("INVALID_MANIFEST")
    if value.keys() != FIELDS:
        raise ValueError("INVALID_MANIFEST_FIELDS")
    if (type(value["schema"]) is not str
            or value["schema"] != "math.universe.candidate.v1"
            or type(value["status"]) is not str
            or value["status"] != "DEV_CANDIDATE"):
        raise ValueError("INVALID_MANIFEST_STATUS")
    for key in ("independentQualification", "executionAuthority",
                "tradingAuthorized"):
        if value[key] is not False:
            raise ValueError("AUTHORITY_DENIED")
    rows = value["repositories"]
    if type(rows) is not list or len(rows) != 4:
        raise ValueError("INVALID_REPOSITORIES")
    seen = set()
    for row in rows:
        if (type(row) is not dict or len(row) != 3
                or any(type(k) is not str for k in row)
                or row.keys() != {"owner", "commit", "tree"}):
            raise ValueError("INVALID_REPOSITORY_FIELDS")
        owner = row["owner"]
        if type(owner) is not str or owner not in OWNERS or owner in seen:
            raise ValueError("INVALID_OWNER")
        seen.add(owner)
        for key in ("commit", "tree"):
            if type(row[key]) is not str or HEX40.fullmatch(row[key]) is None:
                raise ValueError("INVALID_GIT_ID")
