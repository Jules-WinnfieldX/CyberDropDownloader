
class InvalidContentTypeFailure(Exception):
    def __init__(self, *, message: str = "Failed login."):
        self.message = message
        super().__init__(self.message)


class NoExtensionFailure(Exception):
    """This error will be thrown when no extension is given for a file"""
    def __init__(self, *, message: str = "Extension missing for file"):
        self.message = message
        super().__init__(self.message)
