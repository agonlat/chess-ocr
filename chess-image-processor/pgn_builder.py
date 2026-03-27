import chess
import chess.pgn

import chess
import chess.pgn
import io
import re

def build_pgn(game_data, language="EN"):
    board = chess.Board()
    game = chess.pgn.Game()
    
    # --- METADATA (Headers) ---
    metadata = game_data.get("metadata", {})
    for key, value in metadata.items():
        game.headers[key] = str(value)

    # Defaults
    game.headers.setdefault("Event", "OCR Game")
    game.headers.setdefault("White", "Unknown")
    game.headers.setdefault("Black", "Unknown")

    node = game

    # --- MOVES ---
    for move in game_data["moves"]:
        # WHITE
        if move.get("white"):
            try:
                # Engine liefert Englisch -> python-chess verarbeitet es
                m = board.parse_san(move["white"])
                node = node.add_main_variation(m) # WICHTIG: add_main_variation
                board.push(m)
            except Exception:
                print(f"error at white-move: {move['white']}")
                break

        # BLACK
        if move.get("black"):
            if move["black"] == "1/2":
                game.headers["Result"] = "1/2-1/2"
                break
            try:
                m = board.parse_san(move["black"])
                node = node.add_main_variation(m) # WICHTIG: add_main_variation
                board.push(m)
            except Exception:
                print(f"error at black-move: {move['black']}")
                break

    # PGN als String generieren
    pgn_output = str(game)

    # --- ÜBERSETZUNG BEI EXPORT ---
    if language.upper() == "DE":
        # Wir ersetzen die englischen Figurenbuchstaben durch deutsche.
        # Regex sorgt dafür, dass wir nur Figuren am Zuganfang erwischen,
        # nicht die Felder (z.B. b4 bleibt b4, aber B (Bishop) wird L)
        trans = {
            "N": "S", # Springer
            "B": "L", # Läufer
            "R": "T", # Turm
            "Q": "D", # Dame
            # K bleibt K
        }
        for en, de in trans.items():
            # Sucht nach Großbuchstaben, die NICHT am Ende eines Wortes stehen (Koordinate)
            # sondern am Anfang eines Zuges.
            pgn_output = re.sub(fr"(\s|^){en}([a-h]x|[a-h]|[1-8])", fr"\1{de}\2", pgn_output)

    return pgn_output

def save_pgn(pgn_content, filename="game.pgn"):
    # Da build_pgn jetzt einen String (pgn_content) zurückgibt:
    with open(filename, "w", encoding="utf-8") as f:
        f.write(pgn_content)