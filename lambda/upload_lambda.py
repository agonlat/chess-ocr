import json
import base64
import boto3
import uuid

#Create an S3 client using the AWS SDK (boto3)
#This client allows the Lambda function to interact with Amazon S3
s3 = boto3.client("s3")

#Name of the bucket where uploaded images will be stored. 
#This bucket was previously created in AWS

BUCKET = "chess-ocr-score-sheets"

def lambda_handler(event, context):
    """
    Main entry point for the Lambda function.

    Parameters:
    event: contains HTTP request data from API Gateway
    context: provides runtime information about the Lambda execution
    """

    #The request body sent from the frontend is JSON
    #Convert the JSON string into a Python dictionary
    body = json.loads(event["body"])

    #The uploaded image is encoded as Base64 when sent via HTTP
    #Decode the Base64 string back into binary image data
    image_data = base64.b64decode(body["image"])

    #Generate a unique filename using UUID to prevent overwriting files
    #The image will be stored inside the "uploads" folder in the bucket.
    filename = f"uploads/{uuid.uuid4()}.jpg"

    #Upload the decoded image to the S3 bucket
    s3.put_object(
        Bucket = BUCKET, #Target bucket
        Key = filename, #Path and filename in the bucket
        Body = image_data, #Actual binary image data
        ContentType="image/jpeg" #Metadata indicating the file type
    )

    #Return an HTTP response to the client
    #statusCode 200 indicates that the request was successful
    return {
        "statusCode":200,
        "body":json.dumps({
            "message":"Successfully uploaded image",
            "file":filename
        })
    }
