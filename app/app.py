"""Module fetching metadata and sending to SQS"""
import time
import sys
import requests
import boto3

def fetch_metadata(url, max_retries=5):
    """
    Fetch metadata.
    Retry up to max_retries if the request fails.
    """
    retry_delay = 1
    for attempt in range(max_retries):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print("Max retries reached. Giving up.")
                return None

def find_aws_creds(cloud_accounts):
    """
    Find the first cloud account with "type": "AWS_API_CREDENTIAL".
    """
    for account in cloud_accounts.get("cloudAccounts", []):
        for credential in account.get("credentials", []):
            if credential.get("type") == "AWS_API_CREDENTIAL":
                return credential
    return None

def query_metadata(metadata_base_url):
    """
    Query metadata service.
    Retrieve AWS secret, AWS key, SQS URL, and Lab GUID.
    """
    deployment_tags_url = f"{metadata_base_url}/deploymentTags"
    cloud_accounts_url = f"{metadata_base_url}/cloudAccounts"

    deployment_tags = fetch_metadata(deployment_tags_url)
    if deployment_tags is None:
        return None

    cloud_accounts = fetch_metadata(cloud_accounts_url)
    if cloud_accounts is None:
        return None

    try:
        lab_id = deployment_tags.get("LabID")
        sqs_url = deployment_tags.get("SQS")
        aws_credentials = find_aws_creds(cloud_accounts)

        if aws_credentials is None:
            print("AWS API Credentials not found.")
            return None

        aws_secret = aws_credentials.get("secret")
        aws_key = aws_credentials.get("key")

        return {
            "LabID": lab_id,
            "SQS_URL": sqs_url,
            "AWS_Secret": aws_secret,
            "AWS_Key": aws_key
        }
    except (KeyError, IndexError) as e:
        print(f"Error extracting metadata: {e}")
        return None

def send_sqs(queue_url, payload):
    """
    Send payload to SQS
    """
    sqs = boto3.client('sqs')
    try:
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=str(payload)
        )
        return response
    except Exception as e:
        print(f"Error sending message to SQS: {e}")
        return None

def main():
    """
    Main Function
    """
    metadata_base_url = "http://metadata.udf"
    metadata = query_metadata(metadata_base_url)

    if metadata:
        payload = {"LabID": metadata['LabID']}
        max_retries = 6
        retries = 0

        while retries < max_retries:
            success = send_sqs(metadata['SQS_URL'], payload)
            if success:
                print("Message sent to SQS successfully.")
                retries = 0
                retry_delay = 60
            else:
                retries += 1
                retry_delay = 10
                print(f"Error sending SQS message. Retrying in {retry_delay} seconds.")
            time.sleep(retry_delay)
        print("Max SQS retries reached. Exiting.")
        sys.exit(1)
    else:
        print("Failed to retrieve metadata. Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    main()
