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


class CostCeilingExceeded(CadreError):
    def __init__(self, message, *, run_id, budget_used_usd, max_budget_usd):
        super().__init__(message)
        self.run_id = run_id
        self.budget_used_usd = budget_used_usd
        self.max_budget_usd = max_budget_usd


class DoomLoopDetected(CadreError):
    def __init__(self, message, *, model, error_signature, occurrences):
        super().__init__(message)
        self.model = model
        self.error_signature = error_signature
        self.occurrences = occurrences
