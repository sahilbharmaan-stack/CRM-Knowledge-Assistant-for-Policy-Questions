"""Live analytics: every number is aggregated from the SQLite tables on request.

Nothing here is cached or hard-coded, so the dashboard moves as soon as new questions,
reviews or feedback are written. Counsellors only ever see their own rows (user_id scope).
"""
from datetime import datetime, timedelta, timezone

TOPICS = ("refund", "attendance", "programme", "support", "assessment", "freelancing", "other")


def _scope(user_id, alias="q"):
    return (f" AND {alias}.user_id=?", [user_id]) if user_id is not None else ("", [])


def _pct(part, whole):
    return round(100.0 * part / whole, 1) if whole else 0.0


def _percentile(sorted_vals, p):
    if not sorted_vals:
        return 0
    k = (len(sorted_vals) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return int(round(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)))


def _window(conn, user_id, start, end):
    """Headline numbers for [start, end) so the UI can show period-over-period change."""
    s, sp = _scope(user_id)
    row = conn.execute(
        "SELECT COUNT(*) AS total,"
        " SUM(q.status='answered') AS answered, SUM(q.status='abstained') AS abstained,"
        " SUM(q.status='api_error') AS api_error"
        f" FROM staff_queries q WHERE q.created_at>=? AND q.created_at<?{s}",
        [start, end, *sp],
    ).fetchone()
    fb = conn.execute(
        "SELECT SUM(a.feedback='helpful') AS h, SUM(a.feedback='not_helpful') AS n,"
        " AVG(a.latency_ms) AS lat FROM answers a JOIN staff_queries q ON q.id=a.query_id"
        f" WHERE q.created_at>=? AND q.created_at<?{s}",
        [start, end, *sp],
    ).fetchone()
    total = row["total"] or 0
    helpful, not_helpful = fb["h"] or 0, fb["n"] or 0
    return {
        "total": total,
        "answered": row["answered"] or 0,
        "abstained": row["abstained"] or 0,
        "api_error": row["api_error"] or 0,
        "answer_rate": _pct(row["answered"] or 0, total),
        "helpful": helpful,
        "not_helpful": not_helpful,
        "helpful_rate": _pct(helpful, helpful + not_helpful),
        "avg_latency_ms": int(fb["lat"] or 0),
    }


def snapshot(conn, user_id=None, days=14):
    days = max(1, min(int(days), 90))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today = now.date()
    start_day = today - timedelta(days=days - 1)
    fmt = "%Y-%m-%d %H:%M:%S"
    start = datetime.combine(start_day, datetime.min.time()).strftime(fmt)
    end = (now + timedelta(days=1)).strftime(fmt)
    prev_start = (datetime.combine(start_day, datetime.min.time()) - timedelta(days=days)).strftime(fmt)
    s, sp = _scope(user_id)

    current = _window(conn, user_id, start, end)
    previous = _window(conn, user_id, prev_start, start)

    # ---- daily series (zero-filled so the chart axis never has holes)
    by_day = {r["d"]: dict(r) for r in conn.execute(
        "SELECT date(q.created_at) AS d, COUNT(*) AS total,"
        " SUM(q.status='answered') AS answered, SUM(q.status='abstained') AS abstained,"
        " SUM(q.status='api_error') AS api_error"
        f" FROM staff_queries q WHERE q.created_at>=?{s} GROUP BY d",
        [start, *sp],
    )}
    fb_day = {r["d"]: dict(r) for r in conn.execute(
        "SELECT date(q.created_at) AS d, SUM(a.feedback='helpful') AS helpful,"
        " SUM(a.feedback='not_helpful') AS not_helpful, AVG(a.latency_ms) AS latency"
        " FROM answers a JOIN staff_queries q ON q.id=a.query_id"
        f" WHERE q.created_at>=?{s} GROUP BY d",
        [start, *sp],
    )}
    daily = []
    for i in range(days):
        d = (start_day + timedelta(days=i)).isoformat()
        r, f = by_day.get(d, {}), fb_day.get(d, {})
        daily.append({
            "date": d, "total": r.get("total") or 0, "answered": r.get("answered") or 0,
            "abstained": r.get("abstained") or 0, "api_error": r.get("api_error") or 0,
            "helpful": f.get("helpful") or 0, "not_helpful": f.get("not_helpful") or 0,
            "latency_ms": int(f.get("latency") or 0),
        })

    # ---- topics
    topic_rows = {r["topic"] or "other": dict(r) for r in conn.execute(
        "SELECT q.topic AS topic, COUNT(*) AS count, SUM(q.status='abstained') AS abstained,"
        " AVG(q.topic_confidence) AS confidence"
        f" FROM staff_queries q WHERE q.created_at>=?{s} GROUP BY q.topic",
        [start, *sp],
    )}
    topics = sorted(({
        "topic": t, "count": topic_rows[t]["count"], "abstained": topic_rows[t]["abstained"] or 0,
        "confidence": round(topic_rows[t]["confidence"] or 0, 2),
    } for t in topic_rows), key=lambda x: -x["count"])

    # ---- when do people ask? (weekday x hour heat map, UTC)
    heat = [[0] * 24 for _ in range(7)]
    for r in conn.execute(
        "SELECT CAST(strftime('%w', q.created_at) AS INTEGER) AS wd,"
        " CAST(strftime('%H', q.created_at) AS INTEGER) AS hr, COUNT(*) AS c"
        f" FROM staff_queries q WHERE q.created_at>=?{s} GROUP BY wd, hr",
        [start, *sp],
    ):
        heat[(r["wd"] - 1) % 7][r["hr"]] = r["c"]  # Monday first

    # ---- latency distribution
    lat = sorted(r["latency_ms"] for r in conn.execute(
        "SELECT a.latency_ms FROM answers a JOIN staff_queries q ON q.id=a.query_id"
        f" WHERE a.latency_ms IS NOT NULL AND q.created_at>=?{s}",
        [start, *sp],
    ))
    edges = [0, 250, 500, 1000, 2000, 4000, 10**9]
    labels = ["<250", "250-500", "0.5-1s", "1-2s", "2-4s", "4s+"]
    latency_hist = [{"label": labels[i], "count": sum(edges[i] <= v < edges[i + 1] for v in lat)}
                    for i in range(len(labels))]

    # ---- most cited policy documents
    top_docs = [dict(r) for r in conn.execute(
        "SELECT d.doc_code, d.title, d.version, COUNT(DISTINCT p.query_id) AS uses,"
        " ROUND(AVG(p.score), 3) AS avg_score"
        " FROM retrieved_passages p JOIN policy_chunks c ON c.id=p.chunk_id"
        " JOIN policy_documents d ON d.id=c.document_id JOIN staff_queries q ON q.id=p.query_id"
        f" WHERE p.rank=1 AND q.created_at>=?{s} GROUP BY d.id ORDER BY uses DESC LIMIT 6",
        [start, *sp],
    )]

    # ---- review pipeline
    rv = conn.execute(
        "SELECT SUM(a.status='pending_review') AS pending, SUM(a.status='approved') AS approved,"
        " SUM(a.status='rejected') AS rejected, SUM(a.escalated=1) AS escalated,"
        " AVG(CASE WHEN a.reviewed_at IS NOT NULL THEN (julianday(a.reviewed_at)-julianday(a.created_at))*1440 END) AS mins"
        " FROM answers a JOIN staff_queries q ON q.id=a.query_id WHERE 1=1" + s,
        sp,
    ).fetchone()
    review = {k: rv[k] or 0 for k in ("pending", "approved", "rejected", "escalated")}
    review["avg_turnaround_min"] = round(rv["mins"] or 0, 1)

    providers = [dict(r) for r in conn.execute(
        "SELECT COALESCE(a.provider,'n/a') AS provider, COALESCE(a.model,'') AS model, COUNT(*) AS count,"
        " CAST(AVG(a.latency_ms) AS INTEGER) AS avg_latency_ms"
        " FROM answers a JOIN staff_queries q ON q.id=a.query_id"
        f" WHERE q.created_at>=?{s} GROUP BY a.provider, a.model ORDER BY count DESC",
        [start, *sp],
    )]

    people = []
    if user_id is None:
        people = [dict(r) for r in conn.execute(
            "SELECT u.username, COALESCE(u.display_name,u.username) AS name, u.role, COUNT(*) AS questions,"
            " SUM(q.status='answered') AS answered, MAX(q.created_at) AS last_seen"
            " FROM staff_queries q JOIN users u ON u.id=q.user_id WHERE q.created_at>=?"
            " GROUP BY u.id ORDER BY questions DESC LIMIT 6",
            [start],
        )]

    live = [dict(r) for r in conn.execute(
        "SELECT q.id, q.created_at, q.topic, q.status, q.query_text, u.username, a.latency_ms, a.status AS review_status"
        " FROM staff_queries q JOIN users u ON u.id=q.user_id LEFT JOIN answers a ON a.query_id=q.id"
        f" WHERE 1=1{s} ORDER BY q.id DESC LIMIT 12",
        sp,
    )]

    fp = conn.execute(
        "SELECT (SELECT COALESCE(MAX(id),0) FROM staff_queries) AS q,"
        " (SELECT COALESCE(MAX(id),0) FROM answers) AS a,"
        " (SELECT COUNT(*) FROM answers WHERE feedback IS NOT NULL) AS f,"
        " (SELECT COUNT(*) FROM answers WHERE status!='pending_review') AS r"
    ).fetchone()

    return {
        "generated_at": now.strftime(fmt),
        "days": days,
        "fingerprint": f"{fp['q']}-{fp['a']}-{fp['f']}-{fp['r']}",
        "current": current,
        "previous": previous,
        "daily": daily,
        "topics": topics,
        "heatmap": heat,
        "latency": {
            "avg": int(sum(lat) / len(lat)) if lat else 0,
            "p50": _percentile(lat, 0.5), "p95": _percentile(lat, 0.95), "histogram": latency_hist,
        },
        "top_docs": top_docs,
        "review": review,
        "providers": providers,
        "people": people,
        "live": live,
        "policies": {
            r["status"]: r["c"] for r in conn.execute(
                "SELECT status, COUNT(*) AS c FROM policy_documents GROUP BY status")
        },
    }
