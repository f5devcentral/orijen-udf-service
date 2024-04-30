"""Module fetching metadata and sending to SQS"""
import time
import sys
import json
import re
import atexit
import base64  
import yaml 
import requests
import boto3

def b64_lazy_decode(s: str) -> str|None:
    """
    Add padding (=) back and decode.
    Necessary as UDF user tags only support alphanumeric characters
    """
    try:
        this = base64.b64decode(s + "=" * ((4 - len(s)) % 4))
        return this.decode('utf-8').rstrip('\n')
    except Exception as e:
        return None

def fetch_metadata(url: str, max_retries=5) -> dict|None:
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

def find_aws_cred(cloud_accounts: dict) -> dict|None:
    """
    Find the first cloud account with "type": "AWS_API_CREDENTIAL".
    Return a dict containing the cred.
    """
    try:
        for account in cloud_accounts.get("cloudAccounts", []):
            for credential in account.get("credentials", []):
                if credential.get("type") == "AWS_API_CREDENTIAL":
                    return credential
    except Exception as e:
        return None
    
def find_user_tags(meta_tags: list, tags: list) -> dict|None:
    """
    Find user_tags from instance metadata.
    """
    try:
        all_tags = meta_tags[0].get("userTags", [])
        user_tags = {}
        tag_list = [t for t in all_tags if t.get("name") in tags]
        for tag in tag_list:
            user_tags[tag["name"]] = tag["value"]
    except Exception as e:
        return None
    if len(user_tags) == len(tags):
        return user_tags
    else:
        print(f"Unable to find User Tags.")
        return None

def build_sqs_url(region: str, q: str) -> str|None:
    """
    Build a complete SQS queue URL from the pieces in user_tags
    """
    try:
        url = f"https://sqs.{region}.amazonaws.com/{q}"
        return url
    except Exception as e:
        return None

def find_sqs_region(url: str) -> str|None:
    """
    Determine SQS region from URL.
    Boto3 needs this regardless of region in URL.
    """
    try:
        region = re.search(r'sqs\.([\w-]+)\.amazonaws\.com', url).group(1)
        return region
    except AttributeError as e:
        return None

def query_metadata(metadata_base_url: str="http://metadata.udf") -> dict|None:
    """
    Query metadata service.
    Retrieve LabID, DepID, AWS secret, AWS key from various metadata endpoints.
    """
    #Deployment Info
    deployment = fetch_metadata(f"{metadata_base_url}/deployment")
    if deployment is None:
        print("Unable to find Deployment Metadata.")
        return None
    #Runner Info
    runner_user_tags = find_user_tags(fetch_metadata(f"{metadata_base_url}/userTags/name/XC/value/runner"), ["LabID"])
    if runner_user_tags is None:
        print("Unable to find Runner Metadata.")
        return None
    #AWS Info
    aws_credential = find_aws_cred(fetch_metadata(f"{metadata_base_url}/cloudAccounts"))
    if aws_credential is None:
        print("Unable to find AWS Metadata.")
        return None
    #
    try:
        return {
            "depID": deployment.get("deployment")["id"],
            "deployer": deployment.get("deployment")["deployer"],
            "labID": runner_user_tags.get("LabID"),
            "awsSecret": aws_credential.get("secret"),
            "awsKey": aws_credential.get("key")
        }
    except (KeyError, IndexError) as e:
        print(f"Error extracting metadata: {e}")
        return None
        
def get_lab_info(metadata: dict) -> dict|None:
    """
    Get Lab Info from S3.
    """
    try:
        client = boto3.client(
            's3',
            region_name='us-east-1',
            aws_access_key_id=metadata['awsKey'],
            aws_secret_access_key=metadata['awsSecret']
        )
        obj = client.get_object(Bucket='orijen-udf-lab-registry', Key=f"{metadata['labID']}.yaml")
        data = obj['Body'].read().decode('utf-8')
        info = yaml.safe_load(data)
        return info
    except Exception as e:
        print(f"Error retrieving lab info: {e}")
        return None
    
def build_sqs_meta(metadata: dict, lab_info: dict) -> dict|None:
    """
    Build SQS metadata.
    """
    try:
        return {
            "depID": metadata['depID'],
            "deployer": metadata['deployer'],
            "labID": metadata['labID'],
            "sqsURL": lab_info['sqsURL'],
            "region": find_sqs_region(lab_info['sqsURL']),
            "awsKey": metadata['awsKey'],
            "awsSecret": metadata['awsSecret']
        }
    except Exception as e:
        print(f"Error building SQS metadata: {e}")
        return None
    
def send_sqs(metadata: dict, kill: bool=False) -> dict|None:
    """
    Send payload to SQS
    """
    try:
        sqs = boto3.client(
            'sqs', 
            region_name=metadata['region'],
            aws_access_key_id=metadata['awsKey'],
            aws_secret_access_key=metadata['awsSecret']
        )
        message = {
            'id': metadata['depID'],
            'deployer': metadata['deployer'],
            'lab_id': metadata['labID'],
            'kill': kill
        }
    except Exception as e:
        print(f"Error building SQS client and message: {e}")
        return None
    try:
        response = sqs.send_message(
            QueueUrl=metadata['sqsURL'],
            MessageBody=json.dumps(message)
        )
        return response
    except Exception as e:
        print(f"Error sending SQS message: {e}")
        return None

def main():
    """
    Main Function
    """
    metadata = query_metadata()
    labInfo = get_lab_info(metadata)

    sqs_meta = build_sqs_meta(metadata, labInfo)


    if sqs_meta:
        max_retries = 6
        retries = 0

        atexit.register(send_sqs, sqs_meta, True)

        while retries < max_retries:
            success = send_sqs(sqs_meta)
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
