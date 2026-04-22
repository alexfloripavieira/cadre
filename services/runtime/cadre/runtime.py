import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .checkpoint import CheckpointStore
from .errors import (
    CostCeilingExceeded,
    DoomLoopDetected,
    RetryBudgetExceeded,
)
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
    cost_usd: float


class Runtime:
    def __init__(
        self,
        *,
        sep_log_dir: str | Path = ".cadre-log",
        provider: Callable | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        cost_estimator: Callable[[str, Any], float] | None = None,
        checkpoint_store: CheckpointStore | None = None,
    ) -> None:
        self._sep_log = SEPLogger(sep_log_dir)
        self._provider = resolve_provider(provider)
        self._sleep = sleep
        self._clock = clock
        self._cost_estimator = cost_estimator
        self._checkpoint_store = checkpoint_store
        self._budget_used_by_run: dict[str, float] = {}
        self._step_by_run: dict[str, int] = {}

    @property
    def sep_log(self) -> SEPLogger:
        return self._sep_log

    @property
    def checkpoint_store(self) -> CheckpointStore | None:
        return self._checkpoint_store

    def budget_used(self, run_id: str) -> float:
        return self._budget_used_by_run.get(run_id, 0.0)

    def reset_run(self, run_id: str) -> None:
        self._budget_used_by_run.pop(run_id, None)
        self._step_by_run.pop(run_id, None)

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
        accumulated_cost = 0.0

        model_chain = (model, *active_policy.fallback_models)

        for chain_index, current_model in enumerate(model_chain):
            is_primary = chain_index == 0
            recent_error_signatures: list[tuple[str, str]] = []
            doom_loop_triggered = False

            for retry_index in range(1, active_policy.max_retries + 1):
                self._enforce_budget_precheck(resolved_run_id, active_policy)

                total_attempts += 1
                attempt_started = self._clock()
                try:
                    response = self._provider(model=current_model, messages=messages)
                except Exception as exc:
                    last_error = exc
                    signature = _error_signature(exc)
                    recent_error_signatures.append(signature)
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
                                "error_class": signature[0],
                                "error_message": str(exc),
                                "duration_seconds": round(self._clock() - attempt_started, 4),
                            },
                        )
                    )

                    threshold = active_policy.doom_loop_same_error_threshold
                    if (
                        threshold >= 2
                        and len(recent_error_signatures) >= threshold
                        and all(
                            s == recent_error_signatures[-1]
                            for s in recent_error_signatures[-threshold:]
                        )
                    ):
                        logged.append(
                            self._sep_log.write(
                                resolved_run_id,
                                {
                                    "phase": phase,
                                    "agent_role": agent_role,
                                    "model": current_model,
                                    "outcome": "doom_loop_triggered",
                                    "error_signature": list(signature),
                                    "occurrences": len(recent_error_signatures),
                                    "threshold": threshold,
                                },
                            )
                        )
                        doom_loop_triggered = True
                        break

                    is_last_attempt_on_model = retry_index == active_policy.max_retries
                    is_last_model = chain_index == len(model_chain) - 1
                    if not (is_last_attempt_on_model and is_last_model):
                        self._sleep(active_policy.backoff_delay(retry_index))
                    continue

                duration = self._clock() - attempt_started
                cost = self._estimate_cost(current_model, response)
                accumulated_cost += cost
                self._budget_used_by_run[resolved_run_id] = (
                    self._budget_used_by_run.get(resolved_run_id, 0.0) + cost
                )

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
                            "cost_usd": round(cost, 6),
                            "run_budget_used_usd": round(
                                self._budget_used_by_run[resolved_run_id], 6
                            ),
                            "duration_seconds": round(duration, 4),
                        },
                    )
                )

                result = CallResult(
                    response=response,
                    model_used=current_model,
                    attempts=total_attempts,
                    fell_back=not is_primary,
                    duration_seconds=round(self._clock() - overall_started, 4),
                    sep_log_entries=tuple(logged),
                    cost_usd=round(accumulated_cost, 6),
                )

                self._maybe_checkpoint(
                    resolved_run_id,
                    {
                        "phase": phase,
                        "agent_role": agent_role,
                        "model_used": current_model,
                        "fell_back": not is_primary,
                        "attempt_overall": total_attempts,
                        "cost_usd": round(cost, 6),
                        "run_budget_used_usd": round(self._budget_used_by_run[resolved_run_id], 6),
                    },
                )

                return result

            if doom_loop_triggered:
                is_last_model = chain_index == len(model_chain) - 1
                if is_last_model:
                    raise DoomLoopDetected(
                        f"doom loop detected on final model {current_model} "
                        f"for agent {agent_role} in phase {phase}",
                        model=current_model,
                        error_signature=recent_error_signatures[-1],
                        occurrences=len(recent_error_signatures),
                    )
                logged.append(
                    self._sep_log.write(
                        resolved_run_id,
                        {
                            "phase": phase,
                            "agent_role": agent_role,
                            "model": current_model,
                            "outcome": "fallback_triggered",
                            "reason": "doom_loop_on_model",
                            "next_model": model_chain[chain_index + 1],
                        },
                    )
                )
                continue

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

    def _enforce_budget_precheck(self, run_id: str, policy: Policy) -> None:
        if policy.max_budget_usd is None:
            return
        used = self._budget_used_by_run.get(run_id, 0.0)
        if used >= policy.max_budget_usd:
            raise CostCeilingExceeded(
                f"run {run_id} exhausted cost ceiling: used ${used:.4f} "
                f"of ${policy.max_budget_usd:.2f} budget",
                run_id=run_id,
                budget_used_usd=used,
                max_budget_usd=policy.max_budget_usd,
            )

    def _estimate_cost(self, model: str, response: Any) -> float:
        if self._cost_estimator is None:
            return 0.0
        try:
            return float(self._cost_estimator(model, response))
        except Exception:
            return 0.0

    def _maybe_checkpoint(self, run_id: str, data: dict[str, Any]) -> None:
        if self._checkpoint_store is None:
            return
        next_step = self._step_by_run.get(run_id, 0) + 1
        self._step_by_run[run_id] = next_step
        self._checkpoint_store.save(
            run_id=run_id, step_id=next_step, label="call_success", data=data
        )


def _error_signature(exc: Exception) -> tuple[str, str]:
    return (type(exc).__name__, str(exc)[:50])
