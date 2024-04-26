"""Module managing an XC CE Site"""
import time
import sys
import base64   
import requests
import boto3
import yaml

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
    
def fetch_metadata(url: str, max_retries: int=5) -> dict|None:
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
        except Exception as e:
            print(f"Fetch Metadata Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                print("Fetch Metadata Max retries reached. Giving up.")
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
    print("DEBUG")
    print(f"meta_tags: {meta_tags}")
    print(f"tags: {tags}")
    try:
        all_tags = meta_tags[0].get("userTags", [])
        print(f"all_tags: {all_tags}")
        user_tags = {}
        tag_list = [t for t in all_tags if t.get("name") in tags]
        for tag in tag_list:
            user_tags[tag["name"]] = tag["value"]
        print(f"user_tags: {user_tags}")
    except Exception as e:
        return None
    if len(user_tags) == len(tags):
        return user_tags
    else:
        print(f"Unable to find User Tags.")
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
    
def register_ce(metadata: dict, labInfo: dict, metadata_base_url: str="http://metadata.udf", max_retries: int=5) -> dict|None:
    """
    Register CE with XC.
    """
    ce_ip = fetch_metadata(f"{metadata_base_url}/userTags/name/XC/value/CE")[0]["mgmtIp"]
    ce_port = "65500"
    if ce_ip is None:
        print("Unable to find CE IP.")
        return None
    try:
        payload = {
            "hostname": labInfo['siteStatic']['hostname'],
            "latitude": labInfo['siteStatic']['lat'],
            "longitude": labInfo['siteStatic']['long'],
            "cert_hardware": labInfo['siteStatic']['cert_hardware'],
            "primary_outside_nic": labInfo['siteStatic']['primary_outside_nic'],
            "token": labInfo['token'],
            "cluster_name":  f"cluster-{metadata['depID'].split('-')[0]}"
        }
        url = f"https://{ce_ip}:{ce_port}/api/ves.io.vpm/introspect/write/ves.io.vpm.config/update"
        headers = {'Authorization': labInfo['siteStatic']['auth']}
        #
        retry_delay = 10
        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers = headers, verify=False)
                response.raise_for_status()
                if response.status_code == 200 and response.json():
                    return True
            except requests.RequestException as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise Exception("Max retries reached. CE not registered.")
    #
    except Exception as e:
        print(f"Error registering CE: {e}")
        return None

def main():
    """
    Main Function
    """
    metadata = query_metadata()
    labInfo = get_lab_info(metadata)

    if metadata and labInfo:
        success = register_ce(metadata, labInfo)
        if success:
            print("Successfully sent CE registration.")
            sys.exit(0)
        else:
          print(f"Unable to send CE registration. Exiting.")
          sys.exit(1)
    else:
        print("Failed to retrieve needed parameters. Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    main()