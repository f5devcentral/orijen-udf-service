# UDF UserTag Values

This tool uses UDF User tags to pass information on which lab is being launched and which SQS queue should be used to kick off the lab automation.

UDF User Tags, applied to instances, must be < 64 **alphanumeric** characters.
Because this tool needs to pass information such as URLs to the metadata service, these strings will be base64 encoded with the padding removed.

## Padding

Here's an example function to generate tag values:
```python
import base64

def tag_value(s: str) -> str:
    i_bytes = s.encode('utf-8')
    e_bytes = base64.b64encode(i_bytes)
    e_string = e_bytes.decode('utf-8')
    tag_string = e_string.rstrip('=')
    if len(tag_string) > 64:
        raise ValueError(f"String len too long: {len(tag_string)}.")
    return tag_string
```

The padding is added back to these strings before decoding in [``b64_lazy_decode``](./base/app/app.py).

## SQS Values

Standard ARN and URL formatting for SQS queues, once encoded to our tagging format, will bump up against the tagging character limit.
The tool expects 2 tags to be passed into the instance to account for this.

```python

def arn_tag_splitter(arn: str) -> str:
    parts = arn.split(':')
    if (
        len(parts) != 6
        or parts[0] != 'arn' 
        or parts[1] != 'aws'
        or parts[2] != 'sqs'
    ):
        raise ValueError("Invalid ARN format.")
    region = parts[3]
    account = parts[4]
    queue = parts[5]
    return {
        "SQS_r": tag_value(region),
        "SQS_q": tag_value(f"{account}/{queue}")
    }
```

## New Labs

Please reach out to the project owners if you need a new lab created or have questions.