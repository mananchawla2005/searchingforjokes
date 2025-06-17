import time
import threading
import queue
from functools import wraps

def rate_limiter(max_calls, period):
    call_queue = queue.Queue()
    lock = threading.Lock()

    def worker():
        calls = []
        while True:
            func, args, kwargs, result_event = call_queue.get()
            now = time.time()

            with lock:
                # Remove timestamps outside the period window
                calls[:] = [t for t in calls if now - t < period]
                if len(calls) >= max_calls:
                    sleep_time = period - (now - calls[0])
                    time.sleep(max(sleep_time, 0))
                    now = time.time()
                    calls[:] = [t for t in calls if now - t < period]

                calls.append(now)

            try:
                result = func(*args, **kwargs)
                result_event.put(result)
            except Exception as e:
                result_event.put(e)

    threading.Thread(target=worker, daemon=True).start()

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result_event = queue.Queue()
            call_queue.put((func, args, kwargs, result_event))
            result = result_event.get()
            if isinstance(result, Exception):
                raise result
            return result

        return wrapper
    return decorator
