import math
import re
import pandas as pd
from oppenings import get_opening_name


def normalize_name(value):
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def to_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return math.nan


def build_games_dataframe(games):
    rows = []
    for game in games:
        h, white, black = game["headers"], game["white"], game["black"]
        rows.append({
            "game_id": game["game_id"], "event": h.get("Event", ""), "site": h.get("Site", ""),
            "date": h.get("Date", ""), "round": h.get("Round", ""), "white": white, "black": black,
            "white_norm": normalize_name(white), "black_norm": normalize_name(black),
            "result": game["result"], "white_rating": to_int(h.get("WhiteElo")),
            "black_rating": to_int(h.get("BlackElo")), "eco": h.get("ECO", ""),
            "opening": h.get("Opening", ""), "opening_name": get_opening_name(h.get("ECO", ""), h.get("Opening", "")),
            "full_moves": game["full_moves"], "first_10_moves": game["first_10_moves"], "pgn": game["pgn"],
        })
    return pd.DataFrame(rows)


def build_player_dataframe(df, player):
    norm = normalize_name(player)
    out = df[(df.white_norm == norm) | (df.black_norm == norm)].copy()
    out["player_color"] = out.apply(lambda r: "Brancas" if r.white_norm == norm else "Pretas", axis=1)
    out["opponent"] = out.apply(lambda r: r.black if r.player_color == "Brancas" else r.white, axis=1)
    out["player_rating"] = out.apply(lambda r: r.white_rating if r.player_color == "Brancas" else r.black_rating, axis=1)
    out["opponent_rating"] = out.apply(lambda r: r.black_rating if r.player_color == "Brancas" else r.white_rating, axis=1)

    def result(row):
        if row.result == "1/2-1/2": return "Empate"
        if row.result == "1-0": return "Vitória" if row.player_color == "Brancas" else "Derrota"
        if row.result == "0-1": return "Derrota" if row.player_color == "Brancas" else "Vitória"
        return "Não definido"

    out["player_result"] = out.apply(result, axis=1)
    out["is_win"] = out.player_result.eq("Vitória")
    out["is_loss"] = out.player_result.eq("Derrota")
    out["is_draw"] = out.player_result.eq("Empate")
    return out.reset_index(drop=True)


def build_opening_dataframe(df):
    data = df.copy()
    for col, default in [("eco", ""), ("opening_name", "Abertura não informada"), ("first_10_moves", "")]:
        if col not in data.columns:
            data[col] = default
    grouped = data.groupby(["eco", "opening_name", "first_10_moves"], dropna=False).agg(
        partidas=("game_id", "count"), vitorias=("is_win", "sum"), derrotas=("is_loss", "sum"), empates=("is_draw", "sum")
    ).reset_index()
    grouped["aproveitamento"] = (grouped.vitorias + 0.5 * grouped.empates) / grouped.partidas * 100
    grouped = grouped.sort_values(["partidas", "eco", "opening_name"], ascending=[True, True, False]).reset_index(drop=True)
    grouped["linha"] = grouped.groupby(["eco", "opening_name"]).cumcount().add(1)
    return grouped
