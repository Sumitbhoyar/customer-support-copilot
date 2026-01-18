# Manual OpenSearch Serverless Index Creation

The Bedrock Knowledge Base requires an OpenSearch Serverless index to exist before it can be created. Follow these steps after the collection is deployed and ACTIVE.

## Prerequisites
- AWS CLI configured with appropriate credentials
- `curl` or similar HTTP client
- The OpenSearch Serverless collection must be ACTIVE

## Steps

### 1. Get the collection endpoint
After deploying the stack (even if it fails on KB creation), get the collection endpoint:

```powershell
aws opensearchserverless list-collections --region eu-west-2
```

Look for the collection named `kb-dev` (or `kb-<environment>`) and note its `collectionEndpoint`.

### 2. Create the index

Use the AWS CLI with SigV4 signing to create the index:

```powershell
# Set variables
$COLLECTION_ENDPOINT = "https://xxxxxx.eu-west-2.aoss.amazonaws.com"  # Replace with actual endpoint
$INDEX_NAME = "default"
$REGION = "eu-west-2"

# Create index with proper mappings for Titan Embed Text v2 (1024 dimensions)
$BODY = @'
{
  "settings": {
    "index.knn": true
  },
  "mappings": {
    "properties": {
      "vector": {
        "type": "knn_vector",
        "dimension": 1024,
        "method": {
          "engine": "faiss",
          "space_type": "l2",
          "name": "hnsw"
        }
      },
      "text": {
        "type": "text"
      },
      "metadata": {
        "type": "text"
      }
    }
  }
}
'@

# Send the request (requires awscurl or similar tool with SigV4 support)
# Install: pip install awscurl
awscurl --service aoss --region $REGION -X PUT "$COLLECTION_ENDPOINT/$INDEX_NAME" -H "Content-Type: application/json" -d $BODY
```

### Alternative: Using Python script

```python
import boto3
import json
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

# Get credentials
session = boto3.Session()
credentials = session.get_credentials()
auth = AWSV4SignerAuth(credentials, 'eu-west-2', 'aoss')

# Collection endpoint (replace with yours)
collection_endpoint = "xxxxxx.eu-west-2.aoss.amazonaws.com"

# Create client
client = OpenSearch(
    hosts=[{'host': collection_endpoint, 'port': 443}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection,
    timeout=300
)

# Index configuration
index_body = {
    "settings": {
        "index.knn": True
    },
    "mappings": {
        "properties": {
            "vector": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "engine": "faiss",
                    "space_type": "l2",
                    "name": "hnsw"
                }
            },
            "text": {"type": "text"},
            "metadata": {"type": "text"}
        }
    }
}

# Create index
response = client.indices.create('default', body=index_body)
print(f"Index created: {response}")
```

### 3. Verify index creation

```powershell
# Check if index exists
awscurl --service aoss --region $REGION -X GET "$COLLECTION_ENDPOINT/_cat/indices"
```

### 4. Redeploy the stack

Once the index is created, redeploy:

```powershell
cdk deploy --require-approval never
```

The Bedrock Knowledge Base should now succeed in creation.

## Troubleshooting

- **403 Forbidden**: Ensure your IAM user/role has the data access policy attached for the collection
- **Index already exists**: If you get a conflict, delete and recreate: `awscurl --service aoss --region $REGION -X DELETE "$COLLECTION_ENDPOINT/$INDEX_NAME"`
- **Collection not ACTIVE**: Wait for the collection status to be ACTIVE before creating the index

## Notes

- Vector dimension: 1024 (Titan Embed Text v2)
- Index name: `default` (matches the CDK configuration)
- Engine: **faiss** with HNSW algorithm (Bedrock requires FAISS, not nmslib!)
