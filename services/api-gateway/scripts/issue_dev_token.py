import httpx


def main() -> None:
    response = httpx.post(
        "http://127.0.0.1:9000/token",
        json={
            "subject": "local-user",
            "tenant_id": "local-tenant",
            "scope": "scenarios:read",
        },
        timeout=5,
    )
    response.raise_for_status()
    print(response.json()["access_token"])


if __name__ == "__main__":
    main()
