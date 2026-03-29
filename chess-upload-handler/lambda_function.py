import json
import base64
import boto3
import uuid


s3 = boto3.client('s3')

BUCKET_NAME = "chess-score-sheets-ocr" 

def lambda_handler(event, context):
    try:
        
        body = json.loads(event['body'])
        image_b64 = body['image']
        
       
        if "," in image_b64:
            image_b64 = image_b64.split(",")[1]
            
        image_bytes = base64.b64decode(image_b64)
        
        file_name = f"upload_{uuid.uuid4().hex[:6]}.jpg"
        
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=file_name,
            Body=image_bytes,
            ContentType='image/jpeg'
        )
        
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'S3-Upload erfolgreich!',
                'file': file_name
            })
        }
        
    except Exception as e:
        print(f"Error uploading the image: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e)})
        }