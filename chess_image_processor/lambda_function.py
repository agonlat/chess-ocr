import json
import boto3
import urllib.parse
from extract import extract_chess_data_as_json
from pgn_builder import build_pgn

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ChessGames')

def lambda_handler(event, context):
    try:
        # 1. Dateiname aus dem S3-Trigger Event holen
        bucket = event['Records'][0]['s3']['bucket']['name']
        game_id = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'])
        
        # Lokaler Pfad für die Verarbeitung
        download_path = f"/tmp/{game_id}"
        
        # 2. Bild von S3 herunterladen
        s3.download_file(bucket, game_id, download_path)
        
        # 3. OCR & PGN Analyse (Deine Logik)
        json_str = extract_chess_data_as_json(download_path)
        game_data = json.loads(json_str)
        pgn_string = build_pgn(game_data, language="DE")
        
        # 4. DAS FINALE: DynamoDB aktualisieren
        # Wir überschreiben den 'PROCESSING' Status mit dem Ergebnis
        print(f"DEBUG: PGN Länge: {len(pgn_string)} Zeichen")
        if len(pgn_string) < 50:
            print(f"WARNUNG: PGN ist sehr kurz oder leer: {pgn_string}")
        table.put_item(
            Item={
                'game_id': game_id,
                'status': 'COMPLETED',
                'pgn': pgn_string
            }
        )
        
        print(f"Erfolgreich verarbeitet: {game_id}")
        
    except Exception as e:
        print(f"Fehler bei OCR: {str(e)}")
        # Optional: Fehler in DB schreiben, damit Frontend bescheid weiß
        table.update_item(
            Key={'game_id': game_id},
            UpdateExpression="SET #s = :s, error_message = :e",
            ExpressionAttributeNames={'#s': 'status'},
            ExpressionAttributeValues={':s': 'ERROR', ':e': str(e)}
        )