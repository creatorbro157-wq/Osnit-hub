import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DISPOSABLE_DOMAINS = {
    "tempmail.com",
    "10minutemail.com",
    "guerrillamail.com",
    "mailinator.com",
    "yopmail.com",
}

FREE_PROVIDERS = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "proton.me",
    "protonmail.com",
    "icloud.com",
}


def load_platforms(config_path: Path) -> list[dict]:
    if not config_path.exists():
        return []
    return json.loads(config_path.read_text(encoding="utf-8"))


def check_gravatar(email: str) -> dict:
    normalized = email.strip().lower()
    md5_hash = hashlib.md5(normalized.encode("utf-8")).hexdigest()
    # d=404 ensures Gravatar returns 404 when no custom avatar exists
    url = f"https://www.gravatar.com/avatar/{md5_hash}?d=404&s=200"
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=8) as resp:
            status = getattr(resp, "status", 200)
            if status == 200:
                return {
                    "site": "Gravatar",
                    "category": "avatar",
                    "url": url,
                    "grade": "Confirmed",
                    "evidence": "Public Gravatar image found for email hash",
                }
    except HTTPError as e:
        if e.code == 404:
            return {
                "site": "Gravatar",
                "category": "avatar",
                "url": url,
                "grade": "Not found",
                "evidence": "No custom Gravatar avatar (HTTP 404)",
            }
        return {
            "site": "Gravatar",
            "category": "avatar",
            "url": url,
            "grade": "Possible",
            "evidence": f"Gravatar returned HTTP {e.code}",
        }
    except URLError as e:
        return {
            "site": "Gravatar",
            "category": "avatar",
            "url": url,
            "grade": "Error",
            "evidence": f"Network error: {e.reason}",
        }

    return {
        "site": "Gravatar",
        "category": "avatar",
        "url": url,
        "grade": "Possible",
        "evidence": "Unexpected response from Gravatar",
    }


def check_platform(username: str, platform: dict) -> dict:
    name = platform["name"]
    category = platform.get("category", "general")
    url = platform["url_template"].format(username=username)
    exists_codes = set(platform.get("exists_status", [200]))
    not_found_codes = set(platform.get("not_found_status", [404]))
    not_found_markers = platform.get("not_found_markers", [])

    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    try:
        with urlopen(req, timeout=10) as resp:
            status = getattr(resp, "status", 200)
            body = resp.read(200_000).decode("utf-8", errors="ignore")

            if any(marker.lower() in body.lower() for marker in not_found_markers):
                return {
                    "site": name,
                    "category": category,
                    "url": url,
                    "grade": "Not found",
                    "evidence": f"HTTP {status} with not-found marker matched",
                }

            if status in exists_codes:
                return {
                    "site": name,
                    "category": category,
                    "url": url,
                    "grade": "Username match",
                    "evidence": f"HTTP {status} without not-found markers",
                }

            return {
                "site": name,
                "category": category,
                "url": url,
                "grade": "Possible",
                "evidence": f"HTTP {status} received",
            }
    except HTTPError as e:
        if e.code in not_found_codes:
            return {
                "site": name,
                "category": category,
                "url": url,
                "grade": "Not found",
                "evidence": f"HTTP {e.code} Not Found",
            }
        return {
            "site": name,
            "category": category,
            "url": url,
            "grade": "Possible",
            "evidence": f"HTTP {e.code} during request",
        }
    except URLError as e:
        return {
            "site": name,
            "category": category,
            "url": url,
            "grade": "Error",
            "evidence": f"Network error: {e.reason}",
        }


def run_investigation(email: str, platforms_file: Path = Path("platforms.json")) -> dict:
    email = email.strip()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("Please enter a valid email address.")

    local_part, domain = email.rsplit("@", 1)
    domain_lower = domain.lower()
    username_guess = re.sub(r"[^a-zA-Z0-9._-]", "", local_part)

    findings = [check_gravatar(email)]
    for platform in load_platforms(platforms_file):
        findings.append(check_platform(username_guess, platform))

    confirmed_count = sum(1 for f in findings if f["grade"] == "Confirmed")
    match_count = sum(1 for f in findings if f["grade"] == "Username match")
    possible_count = sum(1 for f in findings if f["grade"] == "Possible")

    is_disposable = domain_lower in DISPOSABLE_DOMAINS
    is_custom_domain = domain_lower not in FREE_PROVIDERS and not is_disposable

    score = (
        confirmed_count * 25
        + match_count * 15
        + possible_count * 5
        + (15 if is_custom_domain else 0)
    )
    exposure_score = min(100, score)

    return {
        "target_email": email,
        "username_pivot": username_guess,
        "domain": domain_lower,
        "domain_type": (
            "disposable"
            if is_disposable
            else ("custom/work" if is_custom_domain else "free-provider")
        ),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "exposure_score": exposure_score,
        "summary": {
            "confirmed": confirmed_count,
            "username_matches": match_count,
            "possible": possible_count,
            "total_checks": len(findings),
        },
        "findings": findings,
    }
