import json
import boto3
import os
import io
#Import custom modules
from extract import extract_chess_data_as_json
from pgn_builder import build_pgn

#Initialize AWS clients outside the handler for better performance
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

table = dynamodb.Table('ChessGames')

def lambda_handler(event, context):
    try:
        #Extract bucket and key from the S3 event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        #Define local path in /tmp/ which is the only writable directory
        file_name = os.path.basename(key)
        download_path = f"/tmp/{file_name}"
        
        print(f"Starting processing for: {key} in bucket: {bucket}")
        
        #Download the image from S3 to Lambda local storage
        s3_client.download_file(bucket, key, download_path)
        
        #Perform OCR extraction and validation via extract.py
        #This returns a JSON string containing the move data
        json_str = extract_chess_data_as_json(download_path)
        game_data = json.loads(json_str)
        
        #Generate PGN format using pgn_builder.py
        pgn_obj = build_pgn(game_data, language="DE")
        pgn_string = str(pgn_obj)
        
        #Save the final result into DynamoDB
        #Using S3 key as the unique game_id
        table.put_item(
            Item={
                'game_id': key,
                'pgn': pgn_string,
                'status': 'COMPLETED',
                'raw_json': json_str,
                'timestamp': str(context.aws_request_id)
            }
        )
        
        print(f"Successfully processed and stored in DynamoDB: {key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Success',
                'game_id': key,
                'pgn': pgn_string
            })
        }

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        #Attempt to log error status to DynamoDB so frontend knows it failed
        try:
            table.put_item(
                Item={
                    'game_id': event['Records'][0]['s3']['object']['key'],
                    'status': 'ERROR',
                    'error_message': str(e)
                }
            )
        except:
            pass
            
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }