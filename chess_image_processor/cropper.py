import boto3
import json
import io
from PIL import Image
# Deine bestehenden Klassen (Stelle sicher, dass die Dateien im selben Ordner liegen)
from engine import Engine
from parser import Parser

# Initialisierung
engine = Engine()
parser = Parser()
sagemaker_runtime = boto3.client('sagemaker-runtime', region_name='us-east-1')
textract = boto3.client('textract', region_name='eu-central-1')

# --- KONFIGURATION ---
SAGEMAKER_ENDPOINT_NAME = "huggingface-pytorch-inference-2026-04-02-08-00-11-182"

def normalize_metadata_key(key_text):
    key = key_text.lower().replace(" ", "")
    if "event" in key or "turnier" in key: return "Event"
    if "datum" in key or "date" in key: return "Date"
    if "runde" in key: return "Round"
    if "weiß" in key or "weiss" in key or "white" in key: return "White"
    if "schwarz" in key or "black" in key: return "Black"
    if "resultat" in key or "result" in key: return "Result"
    if "brett" in key: return "Board"
    return None

def get_text(result, blocks_map):
    """Extrahiert Text aus Textract-Blocks (für Metadaten)"""
    text = ""
    if 'Relationships' in result:
        for relationship in result['Relationships']:
            if relationship['Type'] == 'CHILD':
                for child_id in relationship['Ids']:
                    word = blocks_map[child_id]
                    if word['BlockType'] == 'WORD':
                        text += word['Text'] + " "
    return text.strip()

def get_trocr_prediction(crop_img):
    """Schickt ein Bild-Snippet an den SageMaker TrOCR Endpunkt"""
    img_byte_arr = io.BytesIO()
    crop_img.save(img_byte_arr, format='JPEG')
    payload = img_byte_arr.getvalue()

    try:
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT_NAME,
            ContentType="application/x-image",
            Body=payload
        )
        # Dekodierung der Antwort (Anpassung je nach deinem Modell-Output)
        prediction = response['Body'].read().decode("utf-8").strip()
        return prediction
    except Exception as e:
        print(f"SageMaker Fehler: {e}")
        return ""

def extract_chess_data_as_json(file_path):
    # 1. Bild für Textract und PIL laden
    with open(file_path, "rb") as f:
        image_bytes = f.read()
    
    full_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    width, height = full_image.size

    # 2. Textract Analyse starten
    print(f"Analysiere {file_path} mit Textract (TABLES & FORMS)...")
    response = textract.analyze_document(
        Document={'Bytes': image_bytes},
        FeatureTypes=['TABLES', 'FORMS']
    )

    blocks = response['Blocks']
    block_map = {b['Id']: b for b in blocks}
    
    game_data = {
        "metadata": {},
        "moves": []
    }

    # --- 3. METADATEN (FORMS) ---
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

        if norm_key and val_text:
            game_data["metadata"][norm_key] = val_text

    # --- 4. ZÜGE (TABLES + SAGEMAKER) ---
    for block in blocks:
        if block['BlockType'] == 'TABLE':
            table_cells = {}
            max_col, max_row = 0, 0
            
            # Zellen-IDs sammeln
            for relationship in block.get('Relationships', []):
                for child_id in relationship['Ids']:
                    cell = block_map[child_id]
                    r, c = cell['RowIndex'], cell['ColumnIndex']
                    max_row, max_col = max(max_row, r), max(max_col, c)
                    table_cells[(r, c)] = cell

            # Spaltenweise durchgehen (Spalte 1=Nr, 2=Weiß, 3=Schwarz)
            # col_start springt in 3er Schritten (falls mehrere Tabellen nebeneinander)
            for col_start in range(1, max_col, 3): 
                for r in range(1, max_row + 1):
                    # Header (Zeile 1) überspringen
                    if r == 1: continue

                    # 1. Zugnummer extrahieren (von Textract, da meist gedruckt)
                    num_cell = table_cells.get((r, col_start))
                    num_text = get_text(num_cell, block_map) if num_cell else ""
                    clean_num = "".join(filter(str.isdigit, num_text))

                    if not clean_num: continue

                    # 2. Züge für Weiß und Schwarz (via SageMaker TrOCR)
                    white_cell = table_cells.get((r, col_start + 1))
                    black_cell = table_cells.get((r, col_start + 2))

                    def process_cell(cell_block):
                        if not cell_block: return ""
                        # Geometrie holen
                        bbox = cell_block['Geometry']['BoundingBox']
                        left = bbox['Left'] * width
                        top = bbox['Top'] * height
                        right = (bbox['Left'] + bbox['Width']) * width
                        bottom = (bbox['Top'] + bbox['Height']) * height
                        
                        # Bild ausschneiden & an SageMaker senden
                        crop_img = full_image.crop((left, top, right, bottom))
                        return get_trocr_prediction(crop_img)

                    w_pred = process_cell(white_cell)
                    s_pred = process_cell(black_cell)

                    # In Struktur speichern
                    game_data["moves"].append({
                        "move_no": int(clean_num),
                        "white": parser.normalize(w_pred),
                        "black": parser.normalize(s_pred)
                    })

    # --- 5. VALIDIERUNG ---
    print("Validiere Partie mit Schach-Engine...")
    validated_game_data = engine.validate_game(game_data)
    
    return json.dumps(validated_game_data, indent=4, ensure_ascii=False)

# --- START ---
if __name__ == "__main__":
    IMAGE_PATH = "data/game_002.jpg"
    json_output = extract_chess_data_as_json(IMAGE_PATH)
    
    with open("game_data_final.json", "w", encoding="utf-8") as f:
        f.write(json_output)

    print("\nDaten erfolgreich extrahiert und validiert:")
    print(json_output)