"""
Minimal in-process pub/sub for real-time UI updates.

When an action changes a pipeline (from the web chat, the Telegram bot, …),
we publish an event keyed by pipeline_id. The web editor subscribes via SSE
(/api/v1/pipelines/<id>/events) and redraws live.

In-memory = single-process. For multi-worker gunicorn, run with --workers 1
(suffisant pour la démo) or swap this for Redis pub/sub later.
"""
import json
import queue
import threading

_subscribers = {}          # pipeline_id -> set[Queue]
_lock = threading.Lock()


def subscribe(pipeline_id):
    q = queue.Queue(maxsize=100)
    with _lock:
        _subscribers.setdefault(pipeline_id, set()).add(q)
    return q


def unsubscribe(pipeline_id, q):
    with _lock:
        subs = _subscribers.get(pipeline_id)
        if subs:
            subs.discard(q)
            if not subs:
                _subscribers.pop(pipeline_id, None)


def publish(pipeline_id, event_type, payload=None):
    """Fan-out an event to all subscribers of a pipeline."""
    msg = json.dumps({'type': event_type, 'payload': payload or {}})
    with _lock:
        subs = list(_subscribers.get(pipeline_id, ()))
    for q in subs:
        try:
            q.put_nowait(msg)
        except queue.Full:
            pass
