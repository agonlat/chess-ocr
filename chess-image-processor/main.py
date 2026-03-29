import json
from extract import extract_chess_data_as_json
from pgn_builder import build_pgn, save_pgn

# 1. JSON holen
json_str = extract_chess_data_as_json("data/game_002.jpg")
game_data = json.loads(json_str)

# 2. PGN bauen
game = build_pgn(game_data, language = "DE")

# 3. speichern
save_pgn(game, "game.pgn")

print(game)