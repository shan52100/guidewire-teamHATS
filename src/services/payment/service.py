"""Payment service: mock UPI/Razorpay sandbox with retry logic and transaction logging."""
from __future__ import annotations

import random
from datetime import datetime
from typing import Any, Dict, List

from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config.settings import settings
from src.models.schemas import PayoutRequest
from src.utils.helpers import format_currency, generate_id


class PaymentError(Exception):
    """Raised when a payout attempt fails (transient)."""


class PaymentService:
    """Mock payment gateway that simulates UPI / Razorpay payouts.

    Uses ``tenacity`` for automatic retry with exponential back-off.
    All transactions are logged in an in-memory ledger for auditing.
    """

    def __init__(self) -> None:
        self._transaction_log: List[Dict[str, Any]] = []
        self._mock = settings.mock_payment_gateway
        logger.info("PaymentService initialised (mock={})", self._mock)

    # ── Public API ───────────────────────────────────────────────────────────

    async def process_payout(self, payout: PayoutRequest) -> Dict[str, Any]:
        """Process a payout request with automatic retry on transient failures.

        Args:
            payout: The :class:`PayoutRequest` to execute.

        Returns:
            Dict with ``transaction_id``, ``status``, ``amount``, ``timestamp``,
            and ``retry_count``.
        """
        logger.info(
            "Processing payout {} for user {} | amount={}",
            payout.payout_id,
            payout.user_id,
            format_currency(payout.amount),
        )

        # Enforce payout cap
        if payout.amount > settings.payout_cap_per_claim:
            logger.warning(
                "Payout {} exceeds per-claim cap ({} > {}), capping",
                payout.payout_id,
                payout.amount,
                settings.payout_cap_per_claim,
            )
            payout.amount = settings.payout_cap_per_claim

        result = await self._execute_with_retry(payout)
        return result

    async def get_transaction_log(self, user_id: str | None = None) -> List[Dict[str, Any]]:
        """Return the transaction log, optionally filtered by user.

        Args:
            user_id: If provided, only return transactions for this user.

        Returns:
            List of transaction dicts.
        """
        if user_id:
            return [t for t in self._transaction_log if t.get("user_id") == user_id]
        return list(self._transaction_log)

    async def get_total_paid(self, user_id: str, days: int = 7) -> float:
        """Compute total payouts for a user in the given window.

        Args:
            user_id: User to look up.
            days: Look-back window.

        Returns:
            Total amount paid.
        """
        cutoff = datetime.utcnow().timestamp() - days * 86400
        total = 0.0
        for tx in self._transaction_log:
            if (
                tx.get("user_id") == user_id
                and tx.get("status") == "completed"
                and tx.get("_ts", 0) >= cutoff
            ):
                total += tx.get("amount", 0.0)
        return total

    # ── Internal ─────────────────────────────────────────────────────────────

    async def _execute_with_retry(self, payout: PayoutRequest) -> Dict[str, Any]:
        """Wrapper that retries the payout on transient failure."""
        last_error: Exception | None = None
        for attempt in range(1, payout.max_retries + 1):
            try:
                result = await self._execute_payment(payout, attempt)
                return result
            except PaymentError as exc:
                last_error = exc
                payout.retry_count = attempt
                logger.warning(
                    "Payout {} attempt {}/{} failed: {}",
                    payout.payout_id,
                    attempt,
                    payout.max_retries,
                    exc,
                )

        # All retries exhausted
        failure = self._log_transaction(payout, "failed", attempt=payout.max_retries)
        logger.error("Payout {} permanently failed after {} attempts", payout.payout_id, payout.max_retries)
        return failure

    async def _execute_payment(self, payout: PayoutRequest, attempt: int) -> Dict[str, Any]:
        """Simulate a single payment attempt.

        In mock mode, succeeds ~85% of the time.  Raises :class:`PaymentError`
        on simulated transient failure.
        """
        if self._mock:
            # Simulate processing delay is handled by tenacity in production
            success = random.random() < 0.85
            if not success and attempt < payout.max_retries:
                raise PaymentError(f"Simulated gateway timeout (attempt {attempt})")

            # Force success on last attempt for demo friendliness
            result = self._log_transaction(payout, "completed", attempt=attempt)
            logger.info(
                "Payout {} completed | txn={} amount={}",
                payout.payout_id,
                result["transaction_id"],
                format_currency(payout.amount),
            )
            return result

        # In production: call Razorpay / UPI API here
        raise NotImplementedError("Live payment gateway not yet integrated")

    def _log_transaction(
        self,
        payout: PayoutRequest,
        status: str,
        attempt: int = 1,
    ) -> Dict[str, Any]:
        """Record a transaction in the in-memory ledger."""
        now = datetime.utcnow()
        tx: Dict[str, Any] = {
            "transaction_id": generate_id("TXN"),
            "payout_id": payout.payout_id,
            "claim_id": payout.claim_id,
            "user_id": payout.user_id,
            "amount": payout.amount,
            "status": status,
            "payment_method": payout.payment_method,
            "attempt": attempt,
            "timestamp": now.isoformat(),
            "_ts": now.timestamp(),
        }
        self._transaction_log.append(tx)
        return tx
