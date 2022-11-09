class MyTargetUnknownHttpMethod(Exception):
    pass


class MyTargetTokenLimitError(Exception):
    pass


class MyTargetInvalidTokenError(Exception):
    pass


class MyTargetExpiredTokenError(Exception):
    pass


class MyTargetOtherError(Exception):
    pass


class MyTargetMaxAttemptCountError(Exception):
    pass
