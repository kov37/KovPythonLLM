"""Dashboard server entrypoint pinned to loopback."""

import uvicorn


def main() -> None:
    uvicorn.run(
        "KOV.api.app:create_app",
        factory=True,
        host="127.0.0.1",
        port=8787,
        access_log=False,
    )


if __name__ == "__main__":
    main()
