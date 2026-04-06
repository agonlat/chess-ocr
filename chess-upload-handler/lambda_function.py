import json
import base64
import boto3
import uuid

# Clients initialisieren
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET_NAME = "chess-score-sheets-ocr" 
TABLE_NAME = "ChessGames"
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    try:
        # 1. Bild aus Request extrahieren
        body = json.loads(event['body'])
        image_b64 = body['image']
        
        if "," in image_b64:
            image_b64 = image_b64.split(",")[1]
            
        image_bytes = base64.b64decode(image_b64)
        
        # 2. Eindeutige ID generieren (WICHTIG: Diese muss in S3 und DB gleich sein)
        file_name = f"upload_{uuid.uuid4().hex[:6]}.jpg"
        
        # 3. In S3 speichern
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=file_name,
            Body=image_bytes,
            ContentType='image/jpeg'
        )
        
        # 4. INITIALEN EINTRAG IN DYNAMODB ERSTELLEN (Das hat gefehlt!)
        # Ohne diesen Schritt findet der Handler später nichts.
        table.put_item(Item={
            'game_id': file_name,
            'status': 'PROCESSING',
            'pgn': 'Analysis has started...'
        })
        
        # 5. Erfolgreich antworten
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'Upload successful, analysis started!',
                'file': file_name  # Diese ID nutzt das Frontend zum Pollen
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }