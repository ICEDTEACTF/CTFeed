# About Event
- **時區都是 utc+0** (要記得轉換)
    - ``datetime.now(timezone.utc)``
    - ``datetime_obj_with_timezone.astimezone(timezone.utc)``
- 在讀取（即使用``read_event()``）的時候，如果不是確定「只會返回最多一個結果」的情境
    - finish_after=``int((datetime.now(timezone.utc) + timedelta(days=settings.DATABASE_SEARCH_DAYS)).timestamp())``
    - 我們需要限制讀出的數量，避免 DoS