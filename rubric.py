import re
from typing import Any, Dict, Optional


HEURISTIC_MAPPING = [
    {"keywords": ["structure", "folder", "architecture", "cau truc"], "key": "structure"},
    {"keywords": ["readability", "clean code", "doc", "chat luong"], "key": "readability"},
    {"keywords": ["widget", "build"], "key": "widgets"},
    {"keywords": ["logic", "service", "controller", "repository"], "key": "logic"},
    {"keywords": ["state", "provider", "bloc", "riverpod", "getx"], "key": "state"},
    {"keywords": ["navigation", "route"], "key": "navigation"},
    {"keywords": ["model", "data", "json"], "key": "models"},
    {"keywords": ["error", "exception", "try-catch", "validate"], "key": "errors"},
    {"keywords": ["responsive", "overflow", "layout"], "key": "responsive"},
    {"keywords": ["reuse", "constant", "duplicate"], "key": "reusability"},
    {"keywords": ["resource", "asset", "pubspec"], "key": "resources"},
    {"keywords": ["performance", "rebuild"], "key": "performance"},
    {"keywords": ["extend", "extensible", "maintain"], "key": "extensibility"},
    {"keywords": ["convention", "naming", "pascal", "camel", "snake"], "key": "convention"},
    {"keywords": ["test", "testing"], "key": "testing"},
]

DEFAULT_CRITERIA_TEXT = """Project structure | 10%
Readable code | 10%
Widget decomposition | 10%
Separation of UI and logic | 10%
State management | 10%
Navigation | 8%
Data models | 8%
Error handling | 8%
Responsive UI | 8%
Code reuse | 6%
Resource management | 6%
Basic performance | 6%
Extensibility | 6%
Coding convention | 6%
Testing or manual verification | 6%"""


def _map_heuristic_key(name: str) -> str:
    normalized = name.lower()
    for item in HEURISTIC_MAPPING:
        if any(keyword in normalized for keyword in item["keywords"]):
            return item["key"]
    return "readability"


def _extract_weight(text: str) -> Optional[float]:
    match = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if not match:
        return None
    return float(match.group(1)) / 100.0


def _clean_criterion_name(text: str) -> str:
    text = re.sub(r"^\s*[-*]\s+", "", text)
    text = re.sub(r"^\s*\d+[\.)]\s*", "", text)
    text = re.sub(r"\s*\(?\d+(?:\.\d+)?\s*%\)?\s*$", "", text)
    return text.strip(" :-\t")


def _looks_like_code_or_noise(line: str) -> bool:
    stripped = line.strip()
    lowered = stripped.lower()
    if not stripped:
        return True
    if set(stripped) <= set("(){}[];,.:|-_ "):
        return True
    if stripped.endswith(("/", "(", "{", "[", ";", ",", "),", "},", "],")):
        return True
    if ":" in stripped and "|" not in stripped:
        return True
    if any(token in stripped for token in ["//", "=>", "['", '["', "];"]):
        return True
    if lowered.startswith(("import ", "return ", "final ", "var ", "class ", "widget ", "try ", "catch ")):
        return True
    return False


def _looks_like_criterion_name(line: str) -> bool:
    cleaned = _clean_criterion_name(line)
    if not cleaned or _looks_like_code_or_noise(cleaned):
        return False
    if len(cleaned) > 90:
        return False
    words = cleaned.split()
    if len(words) > 10:
        return False
    return True


def _parse_weight_triplets(lines: list[str]) -> list[Dict[str, Any]]:
    items = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        weight = _extract_weight(stripped)
        if weight is None or not re.fullmatch(r"\d+(?:\.\d+)?\s*%", stripped):
            continue

        if index >= 2 and _looks_like_criterion_name(lines[index - 2]):
            items.append({"name": _clean_criterion_name(lines[index - 2]), "weight": weight})
            continue

        for previous_index in range(index - 1, -1, -1):
            candidate = lines[previous_index].strip()
            if _looks_like_criterion_name(candidate):
                items.append({"name": _clean_criterion_name(candidate), "weight": weight})
                break
    return items


def parse_rubric(criteria_text: Optional[str]) -> Optional[Dict[str, Dict[str, Any]]]:
    if not criteria_text or not criteria_text.strip():
        return None

    raw_items = []
    lines = [raw_line.strip() for raw_line in criteria_text.splitlines() if raw_line.strip()]

    weighted_triplets = _parse_weight_triplets(lines)
    if weighted_triplets:
        raw_items = weighted_triplets

    for raw_line in lines if not raw_items else []:
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if set(line.replace("|", "").strip()) <= {"-"}:
            continue
        if any(header in lowered for header in ["criteria", "rubric", "weight"]) and "|" in line:
            continue

        if "|" in line:
            parts = [part.strip() for part in line.split("|") if part.strip()]
            if not parts:
                continue
            name = _clean_criterion_name(parts[0])
            weight = None
            for part in reversed(parts):
                weight = _extract_weight(part)
                if weight is not None:
                    break
        else:
            name = _clean_criterion_name(line)
            weight = _extract_weight(line)

        if name and _looks_like_criterion_name(name):
            raw_items.append({"name": name, "weight": weight})

    if not raw_items:
        return None

    explicit_weight = sum(item["weight"] for item in raw_items if item["weight"] is not None)
    missing = [item for item in raw_items if item["weight"] is None]
    if missing:
        remaining = max(0.0, 1.0 - explicit_weight)
        even_weight = remaining / len(missing) if remaining > 0 else 1.0 / len(raw_items)
        for item in missing:
            item["weight"] = even_weight

    total_weight = sum(item["weight"] for item in raw_items)
    if total_weight <= 0:
        return None

    rubric = {}
    for item in raw_items:
        normalized_weight = item["weight"] / total_weight
        rubric[item["name"]] = {
            "weight": normalized_weight,
            "key": _map_heuristic_key(item["name"]),
        }

    return rubric
