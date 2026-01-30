# About User
- API 查詢的是**DB 裡的 User**（即使這個 User 已經退出 Guild，或是沒有 Role，或是其他會導致失去權限的場景）
    - 這樣設計的緣由是為了審計方便
    - 但是 API 還是盡量返回 discord user data