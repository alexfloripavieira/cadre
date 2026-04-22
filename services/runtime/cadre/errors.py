class CadreError(Exception):
    pass


class PolicyError(CadreError):
    pass


class RetryBudgetExceeded(CadreError):
    def __init__(self, message, *, attempts, last_error=None):
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


class ProviderCallError(CadreError):
    pass
