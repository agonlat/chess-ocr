import json
import boto3

# Initialisiere DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ChessGames')

def lambda_handler(event, context):
    # Standard-Header für alle Antworten (wichtig für CORS)
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    }
    
    try:
        query_params = event.get('queryStringParameters', {}) or {}
        game_id = query_params.get('game_id')
        
        if not game_id:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({'error': 'Missing game_id parameter'})
            }
        
        response = table.get_item(Key={'game_id': game_id})
        
        if 'Item' not in response:
            # WICHTIG: Status 200 senden, damit das Frontend weiter-pollt
            return {
                'statusCode': 200, 
                'headers': headers,
                'body': json.dumps({'status': 'PROCESSING', 'message': 'Not found in DB yet'})
            }
            
        item = response['Item']
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'game_id': item.get('game_id'),
                'status': item.get('status'),
                'pgn': item.get('pgn'),
                'error': item.get('error_message', '')
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': headers, # Header hier auch mitschicken!
            'body': json.dumps({'error': str(e)})
        }