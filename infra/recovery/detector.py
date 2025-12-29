import core.rollback as rollback

ZOMBIE_STATES = {"applying", "verifying"}

def scan():
    histories = rollback.get_all()

    zombies = []
    for h in histories:
        if h["status"] in ZOMBIE_STATES:
            zombies.append(h)

    return zombies
