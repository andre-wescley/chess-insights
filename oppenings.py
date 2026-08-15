import json
from pathlib import Path



def load_eco_names():
    eco_names = {}
    eco_dir = Path("eco_data")
    if not eco_dir.exists():
        return eco_names

    for file_path in sorted(eco_dir.glob("eco?.json")):
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            for opening in data.values():
                eco = opening.get("eco")
                name = opening.get("name")
                if eco and name and eco not in eco_names:
                    eco_names[eco] = name
        except Exception:
            continue
    return eco_names

ECO_NAMES = load_eco_names()


def get_opening_name(eco, opening=""):
    opening = str(opening or "").strip()
    eco = str(eco or "").strip()
    if opening and opening.lower() not in {"nan", "none"}:
        return opening
    return ECO_NAMES.get(eco, f"Abertura não informada ({eco})")
