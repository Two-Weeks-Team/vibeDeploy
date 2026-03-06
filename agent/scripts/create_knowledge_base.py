#!/usr/bin/env python3
import json
import os
import sys
import time

import httpx

DO_API_BASE = "https://api.digitalocean.com/v2/gen-ai"

KB_CONFIG = {
    "name": "vibedeploy-docs",
    "embedding_model_uuid": "gte-large-v1.5",
    "region": "nyc1",
    "datasources": [
        {
            "type": "WebCrawler",
            "config": {
                "base_url": "https://docs.digitalocean.com/products/app-platform/",
                "max_pages": 50,
            },
        },
        {
            "type": "WebCrawler",
            "config": {
                "base_url": "https://docs.digitalocean.com/products/gradient-ai-platform/",
                "max_pages": 50,
            },
        },
        {
            "type": "WebCrawler",
            "config": {
                "base_url": "https://docs.digitalocean.com/products/databases/postgresql/",
                "max_pages": 30,
            },
        },
    ],
}


def main():
    token = os.getenv("DIGITALOCEAN_API_TOKEN")
    if not token:
        print("Error: DIGITALOCEAN_API_TOKEN not set")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    print(f"Creating Knowledge Base: {KB_CONFIG['name']}")
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{DO_API_BASE}/knowledge-bases",
            headers=headers,
            json=KB_CONFIG,
        )

        if response.status_code not in (200, 201):
            print(f"Error {response.status_code}: {response.text}")
            sys.exit(1)

        kb_data = response.json()
        kb_id = kb_data.get("knowledge_base", {}).get("uuid", "")
        print(f"Knowledge Base created: {kb_id}")
        print(f"Add to .env.test: DO_KNOWLEDGE_BASE_ID={kb_id}")

        print("Waiting for indexing...")
        for i in range(30):
            time.sleep(10)
            status_resp = client.get(f"{DO_API_BASE}/knowledge-bases/{kb_id}", headers=headers)
            if status_resp.status_code == 200:
                status = status_resp.json().get("knowledge_base", {}).get("status", "")
                print(f"  [{i * 10}s] Status: {status}")
                if status == "active":
                    print("Knowledge Base is ready!")
                    print(json.dumps(status_resp.json(), indent=2))
                    return
        print("Timed out waiting for KB to become active. Check DO Console.")


if __name__ == "__main__":
    main()
