async def create_github_repo(name: str, files: dict) -> dict:
    _ = (name, files)
    return {"url": "https://github.com/example/repo"}


async def push_files(repo: dict, files: dict) -> dict:
    _ = (repo, files)
    return {"status": "ok"}
