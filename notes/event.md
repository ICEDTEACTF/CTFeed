# About Event
## Rules
- **時區都是 utc+0** (要記得轉換)
    - ``datetime.now(timezone.utc)``
    - ``datetime_obj_with_timezone.astimezone(timezone.utc)``
- 批量讀取 Event
  - 使用 ``read_event_many()``
  - ``finish_after`` mode: ``finish_after=int((datetime.now(timezone.utc) + timedelta(days=settings.DATABASE_SEARCH_DAYS)).timestamp())``
  - 我們需要限制讀出的數量，避免 DoS
  - 為避免日後讀取程式碼困難，使用不同的 mode 需要明確傳參（如 finish_before=None，就算是 None 也要傳）
- 請確保在操作 Database 中的 events table 時遵循以下流程，並確保整個流程被包覆在``try...except...finally...``中：
  1. 使用 ``src.crud.read_event(..., lock=True, duration=120) 對單個 event 加鎖，並獲取物件
  2. （如果有需要，如創建頻道後將 ID 更新到資料庫）操作 Discord Bot
  3. 更新資料庫中的資料
  4. 在``finally...``區塊中解鎖
  5. 如有發生錯誤，在``except...``區塊中 rollback（例如：刪除創建出來的 Discord channel）
  - 純讀取不受此限制

## Docs

### ``read_event_one``

#### 用途
- 用於讀取單一 Event（以 ``id`` 為主鍵）
- 可選擇是否同時嘗試加鎖（給後續更新流程使用）

#### 使用方法
- 只讀取（不加鎖）
    - ``lock=False``
    - 回傳：``(event_db, None)``
- 讀取並嘗試加鎖
    - ``lock=True`` 且 ``duration`` 必填
    - 成功：回傳 ``(event_db, lock_owner_token)``
    - Event 不存在：``NotFoundError``
    - Event 已被鎖住：``LockedError``
- ``type`` 可為 ``ctftime`` / ``custom`` / ``None``，用來限制 Event 類型
- ``archived`` 可為 ``True`` / ``False`` / ``None``，用來限制封存狀態

#### 設計說明
- 單筆查詢一律以 ``Event.id`` 為核心條件
- 加鎖模式採用原子條件更新（``locked_until`` + ``locked_by``）避免競態
- 回傳的 ``lock_owner_token`` 需在後續 ``update_event`` / ``unlock_event`` 使用


### ``read_event_many``

#### 用途
- 用於讀取多筆 Event，給 API 列表查詢與背景工作使用
- 支援 ``ctftime`` 與 ``custom`` 兩種查詢模式

#### 使用方法
- ``type=ctftime``
    - ``finish_after`` mode
        - 只傳 ``finish_after``
        - 不能同時傳 ``finish_before``、``limit``、``before_id``
    - ``finish_before`` mode
        - ``finish_after`` 必須是 ``None``
        - ``limit`` 必填且需大於 0
        - 第一頁：``finish_before=None`` 且 ``before_id=None``
        - 下一頁：帶上前一頁最後一筆的 ``finish`` 和 ``id``（即 ``finish_before``、``before_id``）
- ``type=custom``
    - ``limit`` 必填且需大於 0
    - 第一頁：``before_id=None``
    - 下一頁：帶上前一頁最後一筆 ``id`` 到 ``before_id``
- 不能傳 ``finish_after`` / ``finish_before``
- ``archived`` 可選，用於限制封存狀態

#### 設計說明
- ``ctftime`` 分頁採用複合游標條件：
    - 排序：``ORDER BY finish DESC, id DESC``
    - 下一頁條件：``finish < finish_before`` 或 ``(finish == finish_before and id < before_id)``
- ``custom`` 分頁採用 ``id`` 游標：
    - 排序：``ORDER BY id DESC``
    - 下一頁條件：``id < before_id``
- 參數組合會在函式內做嚴格檢查，不合法時拋 ``ValueError``


### ``ctfmenu``（EventMenu / EventDetailMenu）

#### 用途
- Discord 互動式 Event 清單檢視（ctftime / custom）
- 提供分頁、切換 type、查看單筆 Event 詳細資訊

#### 設計說明
- View timeout 設為 ``60s``，避免互動元件長時間掛著
- ``ctftime`` 清單採「首次查詢後快取」：
  - 第一次 ``build_embed_and_view()`` 查一次資料庫
  - 後續翻頁只吃記憶體快取，不重查 DB
- ``custom`` 清單採 cursor 分頁（``before_id`` + ``limit``）：
  - 每頁查 ``per_page + 1`` 判斷 ``has_next``
  - 使用 page cache（以頁碼快取已讀頁資料）避免回上一頁時被新資料擠動
- ``EventDetailMenu`` 使用 ``read_event_one(lock=False, ...)`` 讀單筆，找不到時回傳 ``Event not found``

#### 常見坑
- ``custom`` 分頁如果每次都重查 DB（不做頁面快取），新資料插入後會造成頁面漂移或看起來「有些 event 被擠掉」
- ``ctftime`` 模式若每次翻頁都重查 DB，會有不必要的負擔；此場景改用快取較穩定
- ``read_event_many`` 需明確傳 mode 參數（即使是 ``None`` 也傳）以提升可讀性並符合本專案規範
- ``read_event_one`` / lock 流程內部使用 ``session.begin()``，caller 不要在外層再包 transaction 以避免巢狀交易風險
