import json

from app.streaming.event import StreamEvent


def sse(event: StreamEvent, data: dict | str) -> str:
    if isinstance(data, dict):
        data = json.dumps(data)

    return f"event: {event.value}\ndata: {data}\n\n"


'''
Example output

event: token
data: Hello

event: token
data: world

event: done
data: {}
'''