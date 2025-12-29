class Executor:
    def __init__(self, *, dry_run: bool = False):
        self.dry_run = dry_run

    def execute(self, snapshot):
        if self.dry_run:
            return self._verify(snapshot)
        return self._apply(snapshot)

    def _verify(self, snapshot):
        if hasattr(snapshot, "verify"):
            return snapshot.verify()
        return True

    def _apply(self, snapshot):
        if hasattr(snapshot, "apply"):
            return snapshot.apply()
        raise RuntimeError("Snapshot is not executable")
