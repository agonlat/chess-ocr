import boto3
import json
from engine import Engine
from parser import Parser

engine = Engine()
parser = Parser()

def normalize_metadata_key(key_text):
    key = key_text.lower().replace(" ", "")

    if "event" in key or "turnier" in key:
        return "Event"
    if "datum" in key or "date" in key:
        return "Date"
    if "runde" in key:
        return "Round"
    if "weiß" in key or "weiss" in key or "white" in key:
        return "White"
    if "schwarz" in key or "black" in key:
        return "Black"
    if "resultat" in key or "result" in key:
        return "Result"
    if "brett" in key:
        return "Board"

    return None

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
    child_to_block = {b['Id']: b for b in blocks if b['BlockType'] == 'WORD'}

    # Endergebnis-Struktur
    game_data = {
        "metadata": {},
        "moves": []
    }

    # --- 1. HELFERFUNKTION FÜR TEXT ---
    def get_text(result, blocks_map):
        text = ""
        if 'Relationships' in result:
            for relationship in result['Relationships']:
                if relationship['Type'] == 'CHILD':
                    for child_id in relationship['Ids']:
                        word = blocks_map[child_id]
                        if word['BlockType'] == 'WORD':
                            text += word['Text'] + " "
        return text.strip()

    # --- 2. METADATEN (FORMS) ---
    key_map = {b['Id']: b for b in blocks if b['BlockType'] == 'KEY_VALUE_SET' and 'KEY' in b['EntityTypes']}
    value_map = {b['Id']: b for b in blocks if b['BlockType'] == 'KEY_VALUE_SET' and 'VALUE' in b['EntityTypes']}

    for key_id, key_block in key_map.items():
        value_block = None
        if 'Relationships' in key_block:
            for rel in key_block['Relationships']:
                if rel['Type'] == 'VALUE':
                    for val_id in rel['Ids']:
                        value_block = value_map.get(val_id)
        
        key_text = get_text(key_block, block_map)
        val_text = get_text(value_block, block_map) if value_block else ""
        
        norm_key = normalize_metadata_key(key_text)

        norm_key = normalize_metadata_key(key_text)

        if norm_key and val_text:
            game_data["metadata"][norm_key] = val_text


    # --- 3. ZÜGE (TABLES) ---
    for block in blocks:
        if block['BlockType'] == 'TABLE':
            table_data = {}
            max_col, max_row = 0, 0
            
            for relationship in block.get('Relationships', []):
                for child_id in relationship['Ids']:
                    cell = block_map[child_id]
                    r, c = cell['RowIndex'], cell['ColumnIndex']
                    max_row, max_col = max(max_row, r), max(max_col, c)
                    
                    text = ""
                    if 'Relationships' in cell:
                        for child_rel in cell['Relationships']:
                            for word_id in child_rel['Ids']:
                                text += child_to_block[word_id]['Text'] + " "
                    table_data[(r, c)] = text.strip()

            # Spaltenweise (Block 1-3, dann 4-6) durchgehen
            for col_start in range(1, max_col, 3): 
                for r in range(1, max_row + 1):
                    num_raw = table_data.get((r, col_start), "")
                    w = table_data.get((r, col_start + 1), "")
                    s = table_data.get((r, col_start + 2), "")
                    
                    clean_num = "".join(filter(str.isdigit, num_raw))
                    if clean_num:
                        game_data["moves"].append({
                            "move_no": int(clean_num),
                            "white": parser.normalize(w),
                            "black": parser.normalize(s)
                        })
    validated_game_data = engine.validate_game(game_data)
    
    return json.dumps(validated_game_data, indent=4, ensure_ascii=False)

# --- AUFRUF UND SPEICHERN ---
#json_output = extract_chess_data_as_json("data/game_002.jpg")

# In Datei speichern
#with open("game_data.json", "w", encoding="utf-8") as f:
    #f.write(json_output)

#print("Daten erfolgreich als JSON extrahiert.")
#print(json_output)



