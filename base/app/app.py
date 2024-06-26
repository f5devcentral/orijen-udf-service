"""Module fetching metadata and sending to SQS"""
import time
import sys
import json
import re
import atexit
import base64   
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
    
def find_user_tags(meta_tags: list) -> dict|None:
    """
    Find user_tags from instance metadata.
    Return a dict with all b64 decoded tags.
    """
    try:
        all_tags = meta_tags[0].get("userTags", [])
        tags = ["LabID", "SQS_r", "SQS_q"]
        user_tags = {}
        tag_list = [t for t in all_tags if t.get("name") in tags]
        for tag in tag_list:
            user_tags[tag["name"]] = b64_lazy_decode(tag["value"])
    except Exception as e:
        return None
    if len(user_tags) == 3:
        return user_tags
    else:
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

def query_metadata(metadata_base_url: str) -> dict|None:
    """
    Query metadata service.
    Retrieve AWS secret, AWS key, SQS URL, Lab GUID, deployer, deploy ID, and region.
    """
    deployment_url = f"{metadata_base_url}/deployment"
    user_tags_url = f"{metadata_base_url}/userTags/name/XC/value/runner"
    cloud_accounts_url = f"{metadata_base_url}/cloudAccounts"
    deployment = fetch_metadata(deployment_url)
    if deployment is None:
        print("Unable to find deployment data.")
        return None
    user_tags = find_user_tags(fetch_metadata(user_tags_url))
    if user_tags is None:
        print("Unable to find user tags.")
        return None
    aws_credential = find_aws_cred(fetch_metadata(cloud_accounts_url))
    if aws_credential is None:
        print("Unable to find AWS metadata.")
        return None
    try:
        dep_id = deployment.get("deployment")["id"]
        deployer = deployment.get("deployment")["deployer"]
        lab_id = user_tags.get("LabID")
        sqs_url = build_sqs_url(user_tags.get("SQS_r"), user_tags.get("SQS_q"))
        region = find_sqs_region(sqs_url)
        return {
            "depID": dep_id,
            "deployer": deployer,
            "labID": lab_id,
            "sqsURL": sqs_url,
            "awsSecret": aws_credential.get("secret"),
            "awsKey": aws_credential.get("key"),
            "region": region
        }
    except (KeyError, IndexError) as e:
        print(f"Error extracting metadata: {e}")
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
    metadata_base_url = "http://metadata.udf"
    metadata = query_metadata(metadata_base_url)

    if metadata:
        max_retries = 6
        retries = 0

        atexit.register(send_sqs, metadata, True)

        while retries < max_retries:
            success = send_sqs(metadata)
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
