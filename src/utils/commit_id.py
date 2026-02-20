import asyncio
import logging

# logging
logger = logging.getLogger("uvicorn")


# functions
async def get_commit_id(timeout_sec: float = 3.0) -> str:
    try:
        process = await asyncio.create_subprocess_exec(
            "git",
            "rev-parse",
            "--short",
            "HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_sec)
        if process.returncode != 0:
            logger.error(f"fail to read commit id: {stderr.decode(errors='replace').strip()}")
            return "unknown"

        commit_id = stdout.decode(errors="replace").strip()
        if len(commit_id) == 0:
            return "unknown"
        return commit_id
    except Exception as e:
        logger.error(f"fail to read commit id: {str(e)}")
        return "unknown"
