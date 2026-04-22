import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal

from .errors import RetryBudgetExceeded
from .policy import Policy
from .providers import resolve_provider
from .sep_log import SEPLogger

Phase = Literal["plan", "execute", "delegate", "review", "decide"]


@dataclass(frozen=True)
class CallResult:
    response: Any
    model_used: str
    attempts: int
    fell_back: bool
    duration_seconds: float
    sep_log_entries: tuple[dict, ...]


class Runtime:
    def __init__(
        self,
        *,
        sep_log_dir: str | Path = ".cadre-log",
        provider: Callable | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._sep_log = SEPLogger(sep_log_dir)
        self._provider = resolve_provider(provider)
        self._sleep = sleep
        self._clock = clock

    @property
    def sep_log(self) -> SEPLogger:
        return self._sep_log

    def call(
        self,
        *,
        run_id: str | None = None,
        agent_role: str,
        phase: Phase,
        model: str,
        messages: list[dict[str, Any]],
        policy: Policy | None = None,
    ) -> CallResult:
        resolved_run_id = run_id or f"run-{uuid.uuid4().hex[:12]}"
        active_policy = policy or Policy()
        active_policy.validate()

        logged: list[dict] = []
        last_error: Exception | None = None
        overall_started = self._clock()
        total_attempts = 0

        model_chain = (model, *active_policy.fallback_models)

        for chain_index, current_model in enumerate(model_chain):
            is_primary = chain_index == 0

            for retry_index in range(1, active_policy.max_retries + 1):
                total_attempts += 1
                attempt_started = self._clock()
                try:
                    response = self._provider(model=current_model, messages=messages)
                except Exception as exc:
                    last_error = exc
                    logged.append(
                        self._sep_log.write(
                            resolved_run_id,
                            {
                                "phase": phase,
                                "agent_role": agent_role,
                                "model": current_model,
                                "is_primary": is_primary,
                                "retry_index": retry_index,
                                "attempt_overall": total_attempts,
                                "outcome": "error",
                                "error_class": type(exc).__name__,
                                "error_message": str(exc),
                                "duration_seconds": round(self._clock() - attempt_started, 4),
                            },
                        )
                    )
                    is_last_attempt_on_model = retry_index == active_policy.max_retries
                    is_last_model = chain_index == len(model_chain) - 1
                    if not (is_last_attempt_on_model and is_last_model):
                        self._sleep(active_policy.backoff_delay(retry_index))
                    continue

                duration = self._clock() - attempt_started
                logged.append(
                    self._sep_log.write(
                        resolved_run_id,
                        {
                            "phase": phase,
                            "agent_role": agent_role,
                            "model": current_model,
                            "is_primary": is_primary,
                            "retry_index": retry_index,
                            "attempt_overall": total_attempts,
                            "outcome": "success",
                            "duration_seconds": round(duration, 4),
                        },
                    )
                )
                return CallResult(
                    response=response,
                    model_used=current_model,
                    attempts=total_attempts,
                    fell_back=not is_primary,
                    duration_seconds=round(self._clock() - overall_started, 4),
                    sep_log_entries=tuple(logged),
                )

            if chain_index < len(model_chain) - 1:
                logged.append(
                    self._sep_log.write(
                        resolved_run_id,
                        {
                            "phase": phase,
                            "agent_role": agent_role,
                            "model": current_model,
                            "outcome": "fallback_triggered",
                            "reason": "primary_retry_budget_exhausted"
                            if is_primary
                            else "fallback_retry_budget_exhausted",
                            "next_model": model_chain[chain_index + 1],
                        },
                    )
                )

        raise RetryBudgetExceeded(
            f"exhausted retry budget on primary and {len(active_policy.fallback_models)} fallback model(s) "
            f"for agent {agent_role} in phase {phase}; total_attempts={total_attempts}",
            attempts=total_attempts,
            last_error=last_error,
        )
