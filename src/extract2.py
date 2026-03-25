import boto3
import json
import chess
import chess.pgn
from difflib import SequenceMatcher

def extract_chess_data_as_json(file_path):
    textract = boto3.client('textract', region_name='eu-central-1')
    with open(file_path, "rb") as f:
        image_bytes = f.read()
    response = textract.analyze_document(
        Document={'Bytes': image_bytes},
        FeatureTypes=['TABLES', 'FORMS']
    )
    blocks = response['Blocks']
    block_map = {b['Id']: b for b in blocks}
    word_map = {b['Id']: b for b in blocks if b['BlockType'] == 'WORD'}

    game_data = {"metadata": {}, "moves": []}

    # --- Helfer: Text aus KEY/VALUE- oder CHILD-Relationships zusammenfügen ---
    def get_text(block):
        text = ""
        if 'Relationships' in block:
            for rel in block['Relationships']:
                if rel['Type'] == 'CHILD':
                    for cid in rel['Ids']:
                        wd = word_map.get(cid)
                        if wd:
                            text += wd['Text'] + " "
        return text.strip()

    # --- Metadaten (Forms) extrahieren ---
    key_map = {b['Id']: b for b in blocks if b['BlockType']=='KEY_VALUE_SET' and 'KEY' in b.get('EntityTypes', [])}
    val_map = {b['Id']: b for b in blocks if b['BlockType']=='KEY_VALUE_SET' and 'VALUE' in b.get('EntityTypes', [])}
    for kid, key_block in key_map.items():
        val_block = None
        if 'Relationships' in key_block:
            for rel in key_block['Relationships']:
                if rel['Type']=='VALUE':
                    for vid in rel['Ids']:
                        val_block = val_map.get(vid)
        key_text = get_text(key_block)
        val_text = get_text(val_block) if val_block else ""
        lt = key_text.lower()
        if key_text and any(x in lt for x in ['event','name','datum','date','resultat','runde','brett']):
            game_data["metadata"][key_text] = val_text

    # --- Züge (TABLES) extrahieren ---
    for block in blocks:
        if block['BlockType'] == 'TABLE':
            table_data = {}
            max_row = max_col = 0
            if 'Relationships' not in block:
                continue
            for rel in block['Relationships']:
                for cid in rel['Ids']:
                    cell = block_map[cid]
                    r, c = cell['RowIndex'], cell['ColumnIndex']
                    max_row = max(max_row, r); max_col = max(max_col, c)
                    # Zelleninhalt zusammensetzen
                    cell_text = ""
                    if 'Relationships' in cell:
                        for crel in cell['Relationships']:
                            for wid in crel['Ids']:
                                word = word_map.get(wid)
                                if word:
                                    cell_text += word['Text'] + " "
                    table_data[(r, c)] = cell_text.strip()
            # Annahme: 3-Spalten-Blöcke (Zugnr., Weiß, Schwarz)
            for col_start in range(1, max_col, 3):
                for row in range(1, max_row+1):
                    num_raw = table_data.get((row, col_start), "")
                    w_move = table_data.get((row, col_start+1), "")
                    b_move = table_data.get((row, col_start+2), "")
                    # Ziffern aus der Move-Nummer extrahieren
                    num = "".join(filter(str.isdigit, num_raw))
                    if num:
                        turn = int(num)
                        # Leere Züge werden als "" erfasst (falls Tabellenzellen leer)
                        game_data["moves"].append({
                            "move_no": turn,
                            "white": w_move,
                            "black": b_move
                        })
    return game_data

# --- Normalisierung und Umwandlung eines Zugs ---
def normalize(move):
    if not move:
        return ""
    m = move.strip()
    # Castling: "0-0-0" -> "O-O-O", "0-0" bzw. "o-o" -> "O-O"
    if m.startswith("0-0-0") or m.startswith("o-o-o"):
        return "O-O-O"
    if m.startswith("0-0") or m.startswith("o-o"):
        return "O-O"
    # Verwechslungen: I/l ↔ 1 (nur sinnvoll für Zahlen)
    m = m.replace("I", "1")
    # Figuren-Erkennung: falls erstes Zeichen ein kleines 'l' ist (für Läufer), großschreiben
    if m and m[0].lower() == 'l':
        m = 'L' + m[1:]
    # Einheitliches Format: erstes Zeichen groß, Rest klein
    if len(m) > 1:
        m = m[0].upper() + m[1:].lower()
    else:
        m = m.upper()
    # Prüfen/Zusatzzeichen entfernen
    if m.endswith(('+', '#')):
        m = m[:-1]
    return m

# --- Deutsche Figuren auf Englisch mappen ---
def german_to_english(move):
    mapping = {"S": "N", "L": "B", "D": "Q", "T": "R", "K": "K"}
    if not move: 
        return move
    first = move[0]
    return mapping.get(first, first) + move[1:]

# --- Ähnlichkeitsfunktion für Fuzzy-Match ---
def similarity(a, b):
    a, b = a.lower(), b.lower()
    if a == b:
        return 1.0
    score = SequenceMatcher(None, a, b).ratio()
    # Bonus, wenn Zielfeld-Teil (letzte 2 Zeichen) übereinstimmt
    if len(a) >= 2 and len(b) >= 2 and a[-2:] == b[-2:]:
        score += 0.2
    return score

def finde_move(token, board):
    """Versucht, den (möglicherweise fehlerhaften) Zug-String token im Board zu finden."""
    cand = normalize(token)
    eng = german_to_english(cand)
    # Direkter SAN-Parse
    try:
        move = board.parse_san(eng)
        return move
    except Exception:
        pass
    # Fallback: Fuzzy-Vergleich aller legalen Züge
    best_move, best_score = None, 0
    for move in board.legal_moves:
        san = board.san(move)
        score = similarity(eng, san)
        if score > best_score:
            best_score, best_move = score, move
    if best_score > 0.65:
        return best_move
    return None

def process_moves(game_data):
    board = chess.Board()
    moves_san = []  # Liste der validen SAN-Züge
    for turn in game_data["moves"]:
        for color in ["white", "black"]:
            raw = turn.get(color)
            if not raw:
                continue
            mv = finde_move(raw, board)
            if mv is not None:
                san = board.san(mv)
                board.push(mv)
                moves_san.append(san)
            else:
                # Nicht erkannt – hier könnte man Fehlerlogik einbauen
                # Wir brechen ab, um Inkonsistenz zu vermeiden:
                print(f"Unbekannter Zug: '{raw}' bei Zug {board.fullmove_number} ({color})")
                return moves_san  # bisherigen Züge zurückgeben
    return moves_san

# --- Hauptablauf: extrahieren, verarbeiten, PGN ausgeben ---
data = extract_chess_data_as_json("data/game_002.jpg")
moves_san = process_moves(data)

# PGN-Spiel erstellen
game = chess.pgn.Game()
# Header setzen (sofern vorhanden)
md = data["metadata"]
game.headers["Event"] = md.get("Event", "?")
game.headers["Date"]  = md.get("Datum", md.get("Date", "????.??.??"))
game.headers["Round"] = md.get("Runde", "?")
game.headers["Result"] = md.get("Resultat", "*")
# Zugfolge ins Spiel einfügen
node = game
for san in moves_san:
    move_obj = board.parse_san(san)
    node = node.add_variation(move_obj)
    board.push(move_obj)

# PGN ausgeben
print(game)

# Optional: JSON-Output speichern
with open("game_data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
