class VerifyAction:
    def __init__(self, action_type, metadata):
        self.action_type = action_type
        self.metadata = metadata

    def verify(self):
        return True
