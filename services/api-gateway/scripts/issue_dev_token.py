import httpx


def main() -> None:
    response = httpx.post(
        "http://127.0.0.1:9999/auth/v1/token",
        params={"grant_type": "password"},
        json={
            "email": "learner@example.com",
            "password": "password",
        },
        timeout=5,
    )
    response.raise_for_status()
    print(response.json()["access_token"])


if __name__ == "__main__":
    main()
