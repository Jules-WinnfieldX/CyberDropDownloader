class JDownloaderFailure(Exception):
    """Basic failure template for JDownloader"""
    def __init__(self, message="Something went wrong"):
        self.message = message
        super().__init__(self.message)


class NoExtensionFailure(Exception):
    """This error will be thrown when no extension is given for a file"""
    def __init__(self, *, message="Extension missing for file"):
        self.message = message
        super().__init__(self.message)


class FailedLoginFailure(Exception):
    """This error will be thrown when the login fails for a site"""
    def __init__(self, *, message="Failed login."):
        self.message = message
        super().__init__(self.message)


class InvalidContentTypeFailure(Exception):
    def __init__(self, *, message="Failed login."):
        self.message = message
        super().__init__(self.message)

class DownloadFailure(Exception):
    """This error will be thrown when a download fails"""
    def __init__(self, code, message="Something went wrong"):
        self.code = code
        self.message = message
        super().__init__(self.message)
        super().__init__(self.code)
