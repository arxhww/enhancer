import core.rollback as rollback

ZOMBIE_STATES = {"defined", "applying", "verifying", "failed"}

def scan():
    histories = rollback.get_all()
    return [h for h in histories if h["status"] in ZOMBIE_STATES]
