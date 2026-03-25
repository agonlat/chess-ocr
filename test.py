import chess
import chess.pgn
import re

# --- Step 1: Full OCR Output ---
ocr_output = """'1","'d4","'sf6","'21","'Sdt","'gxf6","'41","'","'",
"'2","'C4","'e6","'22","'5xt6","'Hg 2","'42","'","'",
"'3","'g3","'d5","'23","'Sdt","'Tcp","'43","'","'",
"'4","'Lg2","'Le7","'24","'5x64","'9+34","'44","'","'",
"'5","'5f3","'0-0","'25","'Tfcn","'Txcn","'45","'","'",
"'6","'0-0","'dxc4","'26","'Txen","'63","'46","'","'",
"'7","'Dcz","'c6","'27","'44","'Tcz","'47","'","'",
"'8","'a4","'65","'28","'T6n","'62","'48","'","'",
"'9","'9x65","'L67","'29","'g 4","'HIG","'49","'","'",
"'10","'Ses","'DC8","'30","'Kg)","'Ket","'50","'","'",
"'11","'bxc6","'Sxc6","'31","'f3","'46","'51","'","'",
"'12","'Sxc6","'Lres","'32","'45","'76","'52","'","'",
"'13","'Dxc4","'Lxg2","'33","'K43","'TeL","'53","'","'",
"'14","'Dxc8","'Txc8","'34","'Kgo","'Tc2","'54","'","'",
"'15","'Kxg2","'at","'35","'","'Kd5","'55","'","'",
"'16","'Sc3","'L64","'36","'Kg3","'Ker","'56","'","'",
"'17","'Ldz","'Td8","'37","'7/2","'712","'57","'","'",
"'18","'e3","'et","'38","'","'","'58","'","'",
"'19","'drer","'Txdz","'39","'","'","'59","'","'",
"'20","'ext6","'TxbL","'40","'","'","'60","'","'"""

# --- Step 2: Split OCR output and extract moves ---
lines = ocr_output.split(",\n")
moves_raw = []
for line in lines:
    tokens = [t.replace("'", "").strip() for t in line.split(",")]
    if len(tokens) >= 3:
        moves_raw.append(tokens[1])  # White move
        moves_raw.append(tokens[2])  # Black move

# --- Step 3: Normalize moves with basic OCR corrections ---
def normalize_move(move):
    move = move.lower().replace(" ", "")
    # Common OCR error corrections
    move = move.replace('s', 'n')  # s -> N (Knight)
    move = move.replace('t', 'r')  # t -> R (Rook)
    move = move.replace('c', 'b')  # c -> B (Bishop)
    move = move.replace('x', 'x')  # Ensure capture x is recognized
    move = re.sub(r'[^a-h1-8nbrqk=+#x-]', '', move)  # Remove garbage
    return move

moves_normalized = [normalize_move(m) for m in moves_raw if m]

# --- Step 4: Automatically validate and reconstruct moves ---
board = chess.Board()
game = chess.pgn.Game()
node = game

valid_moves = []
errors = []

for move_str in moves_normalized:
    try:
        move = board.parse_san(move_str)
        board.push(move)
        node = node.add_variation(move)
        valid_moves.append(board.san(move))
    except ValueError:
        # If move is invalid, try to find a legal move that matches partially
        found = False
        for legal in board.legal_moves:
            if move_str in board.san(legal).lower():
                board.push(legal)
                node = node.add_variation(legal)
                valid_moves.append(board.san(legal))
                found = True
                break
        if not found:
            # Mark as unrecognized
            errors.append(move_str)
            # Optional: insert null move to keep turn count
            # board.push(chess.Move.null())

# --- Step 5: Output results ---
print("Valid moves played:")
print(valid_moves)

print("\nInvalid / unrecognized moves:")
print(errors)

# --- Step 6: Generate PGN ---
pgn_text = str(game)
print("\nGenerated PGN:")
print(pgn_text)