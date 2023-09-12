# flake8: noqa

class InvalidParameterError(Exception):
    pass


class InvalidDataType(InvalidParameterError):
    def __init__(self, mime='', ext=''):
        self.mime = mime
        self.ext = ext

    def __str__(self):
        return f'mime: "{self.mime}", ext: "{self.ext}"'


class NotSupportDrawImage(Exception):
    pass


class NotFound(InvalidParameterError):
    pass


class Timeout(Exception):
    pass
