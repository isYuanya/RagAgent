# Keyword Rankings API

Contracts for the keyword rankings module: industries contain keyword groups,
keyword groups contain imported hotspot videos, and delete operations physically
remove child records.

## Scenario: Keyword Rankings CRUD and CSV Import

### 1. Scope / Trigger

- Trigger: backend or frontend changes touching keyword ranking industries,
  keyword groups, keyword videos, CSV import, ranking, or delete behavior.
- Applies to `app/api/routes/keyword_rankings.py`,
  `app/services/keyword_rankings.py`, keyword ranking ORM models/schemas, and
  frontend calls in `frontend/src/lib/api.ts`.

### 2. Signatures

Backend endpoints:

```text
GET    /api/keyword-industries
POST   /api/keyword-industries
GET    /api/keyword-industries/{industry_id}
DELETE /api/keyword-industries/{industry_id}
GET    /api/keyword-industries/{industry_id}/keywords
POST   /api/keywords
DELETE /api/keywords/{keyword_id}
GET    /api/keywords/{keyword_id}/videos
POST   /api/keyword-videos/import
POST   /api/keyword-videos/crawl
```

CSV import request:

```json
{
  "industry_id": "uuid",
  "keyword": "借钱",
  "csv_text": "source_text,source_url,..."
}
```

Crawler request:

```json
{
  "keyword": "征信查询太多影响贷款吗",
  "min_likes": 1000,
  "max_videos": 50,
  "industry_id": "optional uuid"
}
```

### 3. Contracts

- `industry_id + keyword` identifies a keyword group. Import creates the group
  when it does not already exist.
- Video rows dedupe by `keyword_id + source_url`; existing rows are updated
  instead of duplicated.
- `hot_score` is calculated in the service from likes, comments, favorites, and
  shares using configurable weights, then videos are listed by `hot_score DESC`.
- Deleting an industry physically removes the industry, all keyword groups under
  it, and all videos under those groups.
- Deleting a keyword group physically removes that group and its videos.
- Successful delete responses are `204 No Content` and have no response body.
- `POST /api/keyword-videos/crawl` returns the shared `TaskResponse` contract,
  runs the configured Douyin crawler script in the background, reads the
  generated CSV, and imports it through the same CSV import service. The created
  or updated keyword group name must be the searched keyword.
- Crawler progress is derived from structured `CRAWLER_PROGRESS` lines emitted
  by the script. If fewer videos satisfy `min_likes` than `max_videos`, the
  progress total must shrink to the satisfying-video count rather than staying
  fixed at `max_videos`.

### 4. Validation & Error Matrix

| Condition | Response | Handling |
|---|---|---|
| Missing industry for create/import/list keywords/delete industry | 404 | Return `Keyword industry not found` |
| Missing keyword group for list videos/delete keyword | 404 | Return `Keyword group not found` |
| Duplicate industry name | 409 | Return backend detail from service |
| CSV missing `source_text` header | 200 | Import response has `failed_count = 1` and row error |
| CSV row missing `source_text` | 200 | Row is skipped and reported in `errors` |
| Negative or non-integer metrics | 200 | Row is skipped and reported in `errors` |

### 5. Good/Base/Bad Cases

- Good: importing the same `source_url` twice updates the row and keeps video
  count stable.
- Good: deleting the selected keyword clears its video ranking panel on the
  frontend and refreshes industry counts.
- Good: deleting an industry from the homepage removes the card after refresh.
- Base: deleting a resource that no longer exists returns 404.
- Bad: leaving keyword videos orphaned after deleting a keyword group.
- Bad: parsing a successful 204 delete response as JSON.

### 6. Tests Required

- API tests must cover create industry, create keyword group, CSV import,
  hot-score ordering, duplicate import update, import-created missing keyword,
  keyword deletion removing videos, and industry deletion removing child groups
  and videos.
- Frontend `npm run build` must pass after adding or changing typed API wrappers.

### 7. Wrong vs Correct

#### Wrong

```python
db.delete(industry)
db.commit()
```

This relies entirely on database cascade behavior and can miss cleanup in test
or local database configurations.

#### Correct

```python
db.query(KeywordVideo).filter(KeywordVideo.keyword_id.in_(keyword_ids)).delete(
    synchronize_session=False
)
db.query(KeywordGroup).filter(KeywordGroup.industry_id == industry_id).delete(
    synchronize_session=False
)
db.delete(industry)
db.commit()
```

Delete child records explicitly in the service so behavior is clear and covered
by API tests.
