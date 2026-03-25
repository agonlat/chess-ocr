import chess
from Levenshtein import distance
import re

class Parser:

    @staticmethod
    def translate_to_en(move: str) -> str:
        if not move or move == "1/2":
            return move
        
        # Mapping der deutschen Figuren zu Englisch
        # Wichtig: 'S' (Springer) wird zu 'N' (Knight), 'L' zu 'B' (Bishop), usw.
        translations = {
            "K": "K", # King
            "D": "Q", # Queen
            "T": "R", # Rook
            "L": "B", # Bishop
            "S": "N", # Knight
        }
        
        # Nur das erste Zeichen übersetzen, wenn es eine Figur ist
        if move[0] in translations:
            return translations[move[0]] + move[1:]
        
        return move

    @staticmethod
    def normalize(move: str) -> str:
        if not move or move.strip() == "":
            return ""

        move = move.strip().replace(" ", "")

        # --- SONDERFALL: REMIS (1/2) ---
        # Verhindert, dass aus '1/2' sowas wie 'f/2' wird
        if any(x in move for x in ["1/2", "7/2", "112", "712"]):
            return "1/2"

        # --- ROCHADE ---
        if re.search(r"0-0-0|o-o-o|O-O-O", move, re.IGNORECASE): return "O-O-O"
        if re.search(r"0-0|o-o|O-O", move, re.IGNORECASE): return "O-O"

        chars = list(move)
        
        # --- ERSTES ZEICHEN ---
        first = chars[0]
        # '7' ist fast immer ein 'f' (Bauer)
        if first == "7": chars[0] = "f"
        # '5' oder 's' am Anfang ist oft ein Springer 'S'
        elif first in ["5", "s"] and len(chars) > 1 and not chars[1].isdigit():
            chars[0] = "S"
        # 'D' am Anfang gefolgt von einer Zahl ist fast immer Bauernzug 'd'
        elif first == "D" and len(chars) == 2 and chars[1].isdigit():
            chars[0] = "d"
        # '6' am Anfang ist meist 'b'
        elif first == "6": chars[0] = "b"
        # Generelle Figuren-Großschreibung
        elif first.lower() in ["k", "d", "t", "l", "s"]:
            chars[0] = first.upper()

        # --- LETZTES ZEICHEN (Reihe) ---
        last = chars[-1]
        reihe_map = {"s": "5", "n": "1", "z": "2", "G": "6", "L": "2", "p": "8", "t": "5", "r": "5"}
        if last in reihe_map:
            chars[-1] = reihe_map[last]
        elif last == "g": # Kg -> Kg3 oder hg -> h6
            chars[-1] = "6"

        # --- MITTE (Schlagen & Linien) ---
        if len(chars) >= 3:
            # Wenn das vorletzte Zeichen eine Zahl ist, wo ein Buchstabe sein sollte (Linie)
            prev_char = chars[-2]
            if prev_char == "3": chars[-2] = "b"
            if prev_char == "4": chars[-2] = "h"
            
            # 'r' oder '+' nach einer Figur ist meistens ein 'x' (Schlagen)
            if chars[1] in ["r", "+", "k", "t"] and chars[0].isupper():
                chars[1] = "x"

        # Zusammenfügen
        move = "".join(chars)

        # --- FINALE FORMATIERUNG ---
        if move[0].isupper():
            # Figur: Erster Groß, Rest klein (z.B. Lxe5 statt LXE5)
            move = move[0] + move[1:].lower()
        else:
            # Bauer: Alles klein (z.B. d4 statt D4)
            move = move.lower()

        # Nur erlaubte Zeichen lassen
        move = re.sub(r"[^a-zA-Z0-9xO\-+#/]", "", move)
        
        return move
    