import json
import boto3
import base64
import uuid
from extract import extract_chess_data_as_json
from pgn_builder import build_pgn

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
# Stelle sicher, dass der Bucket-Name hier korrekt hinterlegt ist
S3_BUCKET_NAME = "chess-score-sheets-ocr" 
table = dynamodb.Table('ChessGames')

def lambda_handler(event, context):
    try:
        # 1. Daten aus dem API-Gateway Request extrahieren
        body = json.loads(event['body'])
        image_base64 = body['image']
        
        # Eindeutige ID generieren (muss dem fileName im Frontend entsprechen)
        game_id = f"game_{uuid.uuid4().hex}.jpg"
        download_path = f"/tmp/{game_id}"
        
        # 2. Base64 in Datei umwandeln
        image_bytes = base64.b64decode(image_base64)
        with open(download_path, "wb") as f:
            f.write(image_bytes)
            
        # 3. Bild in S3 sichern (für spätere Analyse/Backup)
        s3_client.upload_file(download_path, S3_BUCKET_NAME, game_id)
        
        # Status in DynamoDB auf 'PROCESSING' setzen
        table.put_item(Item={'game_id': game_id, 'status': 'PROCESSING'})

        # 4. OCR & PGN Erzeugung (Dauert ca. 5-15 Sekunden)
        json_str = extract_chess_data_as_json(download_path)
        game_data = json.loads(json_str)
        pgn_string = build_pgn(game_data, language="DE")
        
        # 5. Finale PGN in DynamoDB speichern
        table.put_item(
            Item={
                'game_id': game_id,
                'pgn': pgn_string,
                'status': 'COMPLETED',
                'timestamp': str(context.aws_request_id)
            }
        )
        
        return {
            'statusCode': 200,
            'headers': {
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json"
            },
            'body': json.dumps({'file': game_id}) # Das Frontend braucht diese ID zum Pollen
        }

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {"Access-Control-Allow-Origin": "*"},
            'body': json.dumps({'error': str(e)})
        }