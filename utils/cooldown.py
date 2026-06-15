import time

COOLDOWN = {}

def allow(key: str, seconds: int) -> bool:
    now = time.time()
    last = COOLDOWN.get(key, 0)

    if now - last < seconds:
        return False

    COOLDOWN[key] = now

    if len(COOLDOWN) > 5000:
        expired_keys = [k for k, v in COOLDOWN.items() if now - v > seconds * 2]
        for k in expired_keys:
            COOLDOWN.pop(k, None)

    return True
    
