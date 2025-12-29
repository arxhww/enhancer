import core.rollback as rollback

ZOMBIE_STATES = {"APPLYING", "VERIFYING"}

def scan():
    histories = rollback.get_all()

    zombies = []
    for h in histories:
        if h["status"] in ZOMBIE_STATES:
            zombies.append(h)

    return zombies
