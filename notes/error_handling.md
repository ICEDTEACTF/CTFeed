# About Error Handling
When an error occured, try to rollback in ``except`` section.
When an error occured in ``except`` section, log it (level CRITICAL).
When an error occured in ``finally`` section, log it (level CRITICAL).

Here's an example:
```python
try:
    # operations
    ...
except Exception as e:
    logger.error(f"fail to ...: {str(e)}")
    try:
        # rollback
        # ...
    except Exception:
        logger.critical("fail to ...: {str(e)}")
finally:
    try:
        # operations
        # for example: unlock
        ...
    except Exception:
        logger.critical(f"fail to ...: {str(e)}")
```

Backend 一律輸出 HTTPException