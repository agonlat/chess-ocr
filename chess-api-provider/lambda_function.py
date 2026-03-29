import json
import boto3
#Initialize DynamoDB resource
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ChessGames')

def lambda_handler(event, context):
    try:
        #Get the game_id from the API request parameters
        #Example URL: /results?game_id=chess_board_001.jpg
        query_params = event.get('queryStringParameters', {})
        game_id = query_params.get('game_id')
        
        if not game_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing game_id parameter'})
            }
        
        #Fetch the item from DynamoDB
        response = table.get_item(Key={'game_id': game_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'body': json.dumps({'status': 'PROCESSING', 'message': 'Not ready yet'})
            }
            
        #Return the stored PGN and status
        item = response['Item']
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*' #Required for Frontend/CORS
            },
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
            'body': json.dumps({'error': str(e)})
        }