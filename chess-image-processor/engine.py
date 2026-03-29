import chess
import re
from jellyfish import jaro_winkler_similarity

class Engine:

    @staticmethod
    def fuzzy_pre_correction(ocr_raw):
        # Liste bekannter Züge zur Vor-Filterung
        common_moves = ["axb5", "Bxc6", "Lb7", "dxc4", "O-O", "Nf3", "d4", "c4", "Nf6", "e6"]
        best_match = ocr_raw
        highest_score = 0
        for candidate in common_moves:
            score = jaro_winkler_similarity(candidate, ocr_raw)
            if score > 0.92:
                if score > highest_score:
                    highest_score = score
                    best_match = candidate
        return best_match

    @staticmethod
    def find_best_legal_move(board, ocr_raw, log_file, side_name, move_no):
        # 1. Vor-Verarbeitung
        pre_fixed = Engine.fuzzy_pre_correction(ocr_raw)
        norm_move = Engine.normalize(pre_fixed)
        translated = Engine.translate_to_en(norm_move)

        if not translated or translated == "1/2": 
            return translated
        
        legal_moves = [board.san(m) for m in board.legal_moves]
        scored_moves = []

        for m in legal_moves:
            # Basis-Ähnlichkeit
            base_score = jaro_winkler_similarity(m, translated)
            final_score = base_score
            
            # --- STRUKTURELLE GEWICHTUNG ---
            
            # A) Längen-Check: Wenn die Länge identisch ist, ist es ein starkes Indiz
            if len(m) == len(translated):
                final_score += 0.08
            
            # B) Schlagzug-Check: 'x' muss übereinstimmen
            if 'x' in translated:
                if 'x' in m:
                    final_score += 0.12  # Starker Bonus für korrekten Schlagzug
                else:
                    final_score -= 0.10  # Abzug, wenn OCR 'x' sieht, der legale Zug aber nicht
            
            # C) Feld-Check: Stimmen die letzten zwei Zeichen (z.B. b7) übereinstimmt?
            if len(translated) >= 2 and len(m) >= 2:
                if translated[-2:] == m[-2:]:
                    final_score += 0.05

            scored_moves.append({
                'san': m,
                'base': base_score,
                'final': final_score,
                'len_diff': abs(len(m) - len(translated))
            })
        
        # Sortierung: 1. Finaler Score hoch, 2. Geringste Längenabweichung
        scored_moves.sort(key=lambda x: (x['final'], -x['len_diff']), reverse=True)
        
        best_move = scored_moves[0]['san'] if scored_moves else None

        # --- SCHREIBE DETAILLIERTEN DEBUG IN TXT ---
        log_file.write(f"\n{'='*70}\n")
        log_file.write(f"ZUG {move_no} ({side_name}) | OCR: '{ocr_raw}' -> NORM: '{translated}'\n")
        log_file.write(f"{'-'*70}\n")
        log_file.write(f"{'Zug':<10} | {'Base':<8} | {'Final':<8} | {'Länge':<6} | {'Status'}\n")
        log_file.write(f"{'-'*10}-+-{'-'*8}-+-{'-'*8}-+-{'-'*6}-+-{'-'*15}\n")
        
        for entry in scored_moves[:5]:
            status = "GEWÄHLT" if entry['san'] == best_move else ""
            log_file.write(f"{entry['san']:<10} | {entry['base']:.4f} | {entry['final']:.4f} | {len(entry['san']):<6} | {status}\n")
        
        log_file.write(f"{'='*70}\n")
        
        return best_move

    @staticmethod
    def validate_game(json_data):
        board = chess.Board()
        corrected_moves = []

        with open("debug_log.txt", "w", encoding="utf-8") as log_file:
            log_file.write("=== SCHACH OCR EXPERTEN-DEBUG LOG ===\n")
            log_file.write("Priorität: Länge > Schlagzug (x) > Feld-Übereinstimmung\n\n")

            for item in json_data["moves"]:
                m_no = item["move_no"]
                
                # WEISS
                w_raw = item["white"]
                if w_raw == "1/2": break
                
                w_fixed = Engine.find_best_legal_move(board, w_raw, log_file, "Weiß", m_no)
                if w_fixed and w_fixed in [board.san(m) for m in board.legal_moves]:
                    board.push_san(w_fixed)
                
                # SCHWARZ
                b_raw = item["black"]
                b_fixed = None
                
                if b_raw == "1/2":
                    b_fixed = "1/2"
                elif b_raw:
                    b_fixed = Engine.find_best_legal_move(board, b_raw, log_file, "Schwarz", m_no)
                    if b_fixed and b_fixed in [board.san(m) for m in board.legal_moves]:
                        board.push_san(b_fixed)

                corrected_moves.append({
                    "move_no": m_no,
                    "white": w_fixed if w_fixed else w_raw,
                    "black": b_fixed if b_fixed else b_raw
                })

                if w_raw == "1/2" or b_raw == "1/2":
                    break
            
        return {"moves": corrected_moves}

    @staticmethod
    def translate_to_en(move: str) -> str:
        if not move or move == "1/2": return move
        translations = {"K": "K", "D": "Q", "T": "R", "L": "B", "S": "N"}
        if len(move) > 0 and move[0] in translations:
            return translations[move[0]] + move[1:]
        return move

    @staticmethod
    def normalize(move: str) -> str:
        if not move or move.strip() == "": return ""
        move = move.strip().replace(" ", "")
        
        if any(x in move for x in ["1/2", "7/2"]): return "1/2"
        if re.search(r"0-0-0|o-o-o|O-O-O", move, re.IGNORECASE): return "O-O-O"
        if re.search(r"0-0|o-o|O-O", move, re.IGNORECASE): return "O-O"
        
        chars = list(move)
        if not chars: return ""
        
        # Erster Buchstabe (Figur vs Bauer)
        if chars[0].lower() in ["k", "d", "t", "l", "s"]:
            chars[0] = chars[0].upper()
        elif chars[0].upper() in "ABCDEFGH" and len(chars) > 1 and chars[1].isdigit():
            chars[0] = chars[0].lower() # Erzwinge Kleinschreibung für Bauern (z.B. c4)
            
        # Schlagzug-Erkennung (OCR liest oft 'r' oder '+' statt 'x')
        if len(chars) >= 3 and chars[0].isupper():
            if chars[1] in ["r", "k", "t", "7", "4"]:
                chars[1] = "x"
                
        move = "".join(chars)
        return re.sub(r"[^a-zA-Z0-9xO\-+#/]", "", move)