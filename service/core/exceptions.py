class AppException(Exception):
    """appexception"""
    def __init__(self, message: str, code: int = 400, data=None):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(message)
