#!/usr/bin/env python3
"""Create OpenSearch Serverless index for Bedrock Knowledge Base."""

import boto3
import sys
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

def main():
    # Get collection endpoint from CloudFormation
    cf = boto3.client('cloudformation', region_name='eu-west-2')
    try:
        resp = cf.describe_stacks(StackName='AISupportStack-dev')
        outputs = {o['OutputKey']: o['OutputValue'] for o in resp['Stacks'][0]['Outputs']}
        collection_endpoint = outputs['CollectionEndpoint'].replace('https://', '')
    except Exception as e:
        print(f"Error getting collection endpoint: {e}")
        sys.exit(1)

    print(f"Creating index on collection: {collection_endpoint}")

    # Get credentials
    session = boto3.Session()
    credentials = session.get_credentials()
    auth = AWSV4SignerAuth(credentials, 'eu-west-2', 'aoss')

    # Create client
    client = OpenSearch(
        hosts=[{'host': collection_endpoint, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=300
    )

    # Index configuration for Titan Embed Text v2 (1024 dimensions)
    # IMPORTANT: Bedrock requires FAISS engine, not nmslib!
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

    # Delete existing index if it exists
    try:
        print("Deleting existing index 'default'...")
        client.indices.delete(index='default')
        print("Old index deleted.")
    except Exception as e:
        print(f"No existing index to delete (or error): {e}")

    # Create index with FAISS engine
    try:
        response = client.indices.create(index='default', body=index_body)
        print("Index created successfully with FAISS engine!")
        print(f"Response: {response}")
    except Exception as e:
        print(f"Error creating index: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
