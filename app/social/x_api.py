"""Read public posts from the X API. This client only sends GET requests."""

import httpx

from app.core.errors import AppError

SEARCH_URL = "https://api.x.com/2/tweets/search/recent"
LOOKUP_URL = "https://api.x.com/2/tweets/{tweet_id}"


def search_recent(token: str, query: str, limit: int) -> list[dict]:
    payload = _get(
        SEARCH_URL,
        token,
        {
            "query": (query or "").strip()[:512],
            "max_results": "10",
            "tweet.fields": "created_at,author_id,conversation_id,text",
            "expansions": "author_id",
            "user.fields": "name,username,description",
        },
    )
    bounded = max(1, min(int(limit or 10), 10))
    return parse_tweets(payload)[:bounded]


def lookup_post(token: str, tweet_id: str) -> dict | None:
    if not str(tweet_id).isdigit():
        return None
    payload = _get(
        LOOKUP_URL.format(tweet_id=tweet_id),
        token,
        {
            "tweet.fields": "created_at,author_id,conversation_id,text",
            "expansions": "author_id",
            "user.fields": "name,username,description",
        },
    )
    rows = parse_tweets(payload)
    return rows[0] if rows else None


def parse_tweets(payload: dict) -> list[dict]:
    if not isinstance(payload, dict):
        return []
    users = {}
    includes = payload.get("includes") or {}
    for user in includes.get("users") or []:
        if isinstance(user, dict) and user.get("id"):
            users[str(user["id"])] = user
    data = payload.get("data")
    if isinstance(data, dict):
        tweets = [data]
    elif isinstance(data, list):
        tweets = data
    else:
        tweets = []
    rows = []
    for tweet in tweets:
        if not isinstance(tweet, dict):
            continue
        tweet_id = str(tweet.get("id") or "")
        author = users.get(str(tweet.get("author_id") or ""), {})
        username = str(author.get("username") or "").strip()
        if not tweet_id or not username:
            continue
        rows.append(
            {
                "platform": "x",
                "url": f"https://x.com/{username}/status/{tweet_id}",
                "poster_name": str(author.get("name") or username)[:250],
                "poster_role": str(author.get("description") or "")[:250],
                "posted_at": tweet.get("created_at") or "",
                "snippet": str(tweet.get("text") or "").strip()[:4000],
                "discussion_key": str(tweet.get("conversation_id") or tweet_id),
                "topic": "US IT vendor hiring",
            }
        )
    return rows


def _get(url: str, token: str, params: dict) -> dict:
    if not (token or "").strip():
        raise AppError("No X API key is configured", 400)
    try:
        with httpx.Client(timeout=20) as client:
            response = client.get(url, headers={"Authorization": f"Bearer {token}"}, params=params)
    except httpx.HTTPError as exc:
        raise AppError(f"X API request failed ({exc.__class__.__name__})", 502) from exc
    if response.status_code in {401, 403}:
        raise AppError("X API key was rejected. Check the key under API keys.", 502)
    if response.status_code == 429:
        raise AppError("X API rate limit reached. Try again later.", 429)
    if response.status_code >= 400:
        raise AppError(f"X API request failed ({response.status_code})", 502)
    try:
        body = response.json()
    except ValueError as exc:
        raise AppError("X API returned an unreadable response", 502) from exc
    if not isinstance(body, dict):
        raise AppError("X API returned an unreadable response", 502)
    return body
