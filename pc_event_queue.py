# pc_event_queue.py
import queue

_event_q = queue.Queue()

def push(event: dict):
    _event_q.put(event)

def pop():
    return _event_q.get()
