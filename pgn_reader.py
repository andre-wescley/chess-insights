import io
import re
import chess.pgn


def split_pgn_games(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []
    starts = [m.start() for m in re.finditer(r'(?m)^\s*\[Event\s+"', text)]
    if not starts:
        return [text]
    return [text[start:end].strip() for start, end in zip(starts, starts[1:] + [len(text)]) if text[start:end].strip()]


def read_pgn_games(handle):
    games, errors = [], []
    for number, block in enumerate(split_pgn_games(handle.read()), 1):
        try:
            game = chess.pgn.read_game(io.StringIO(block))
            if game is None:
                errors.append(f"Bloco {number}: PGN inválido.")
                continue
            board, moves, first_20 = game.board(), [], []
            for ply, move in enumerate(game.mainline_moves(), 1):
                san = board.san(move)
                moves.append(san)
                if ply <= 10:
                    first_20.append(san)
                board.push(move)
            headers = dict(game.headers)
            games.append({
                "game_id": len(games) + 1,
                "headers": headers,
                "white": headers.get("White", "Desconhecido").strip(),
                "black": headers.get("Black", "Desconhecido").strip(),
                "result": headers.get("Result", "*").strip(),
                "first_10_moves": " ".join(first_20),
                "full_moves": (len(moves) + 1) // 2,
                "pgn": block,
            })
        except Exception as exc:
            errors.append(f"Bloco {number}: {exc}")
    return games, errors
