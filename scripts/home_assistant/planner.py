from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .adapters import get_adapter
from .canonical import canonical_hash
from .client import HomeAssistantClient
from .models import (
    ActionType,
    ApplyPlan,
    BaselineRecord,
    DiffReport,
    DiffStatus,
    JournalEntry,
    PlanAction,
    ResourceDocument,
)

LOCK_TIMEOUT_SECONDS = 900.0  # 15 minutes


class LockError(Exception):
    """Raised when the apply lock cannot be acquired."""


class StalePlanError(Exception):
    """Raised when live state diverges from the expected pre-apply state."""


class Planner:
    def __init__(self, repo_root: Path, instance: str = "homelab-01") -> None:
        self.repo_root = repo_root
        self.instance = instance
        self.state_dir = repo_root / ".agent-state" / "home-assistant" / instance
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.lock_file = self.state_dir / "lock.json"
        self.baseline_file = self.state_dir / "baseline.json"
        self.journal_dir = self.state_dir / "journal"
        self.journal_dir.mkdir(parents=True, exist_ok=True)

    def load_baseline(self) -> BaselineRecord | None:
        if not self.baseline_file.is_file():
            return None
        try:
            data = json.loads(self.baseline_file.read_text(encoding="utf-8"))
            return BaselineRecord.from_dict(data)
        except Exception:
            return None

    def save_baseline(self, baseline: BaselineRecord) -> None:
        self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
        self.baseline_file.write_text(
            json.dumps(baseline.to_dict(), indent=2), encoding="utf-8"
        )

    def acquire_lock(self, owner: str, plan_id: str) -> None:
        now = time.time()
        if self.lock_file.is_file():
            try:
                data = json.loads(self.lock_file.read_text(encoding="utf-8"))
                expires_at = data.get("expires_at", 0)
                if now < expires_at:
                    raise LockError(
                        f"Apply lock already held by '{data.get('owner')}' for plan '{data.get('plan_id')}' until {data.get('expires_at')}"
                    )
            except (json.JSONDecodeError, OSError):
                pass  # Corrupt lock file can be overwritten

        lock_data = {
            "owner": owner,
            "plan_id": plan_id,
            "acquired_at": now,
            "expires_at": now + LOCK_TIMEOUT_SECONDS,
        }
        self.lock_file.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")

    def release_lock(self, plan_id: str) -> None:
        if self.lock_file.is_file():
            try:
                data = json.loads(self.lock_file.read_text(encoding="utf-8"))
                if data.get("plan_id") == plan_id:
                    self.lock_file.unlink(missing_ok=True)
            except Exception:
                self.lock_file.unlink(missing_ok=True)

    def record_journal(self, entry: JournalEntry) -> None:
        journal_file = self.journal_dir / f"{entry.plan_id}.jsonl"
        with journal_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

    def create_plan(
        self,
        diff_report: DiffReport,
        git_revision: str,
        baseline_hash: str,
        selected_keys: set[str] | None = None,
    ) -> ApplyPlan:
        """Create an immutable apply plan from a diff report."""
        actions: list[PlanAction] = []
        plan_id = f"plan-{uuid.uuid4().hex[:8]}"

        for item in diff_report.items:
            rk_str = str(item.resource_key)
            if (
                selected_keys is not None
                and rk_str not in selected_keys
                and item.key not in selected_keys
            ):
                continue

            # Check for unresolved conflicts
            if item.status == DiffStatus.CONFLICT:
                raise ValueError(
                    f"Cannot generate plan with unresolved conflict on {rk_str}"
                )

            # Git changes are planned
            if item.status == DiffStatus.GIT_CHANGE:
                if item.baseline_hash is None and item.live_hash is None:
                    # New resource in Git
                    actions.append(
                        PlanAction(
                            kind=item.kind,
                            key=item.key,
                            action=ActionType.CREATE,
                            before=None,
                            after=item.git,
                            expected_live_hash=None,
                        )
                    )
                elif item.git_hash is None:
                    # Deleted from Git
                    actions.append(
                        PlanAction(
                            kind=item.kind,
                            key=item.key,
                            action=ActionType.DELETE,
                            before=item.live,
                            after=None,
                            expected_live_hash=item.live_hash,
                        )
                    )
                else:
                    # Updated in Git
                    actions.append(
                        PlanAction(
                            kind=item.kind,
                            key=item.key,
                            action=ActionType.UPDATE,
                            before=item.live,
                            after=item.git,
                            expected_live_hash=item.live_hash,
                        )
                    )

        now_iso = datetime.now(timezone.utc).isoformat()
        return ApplyPlan(
            plan_id=plan_id,
            timestamp=now_iso,
            instance=self.instance,
            git_revision=git_revision,
            baseline_hash=baseline_hash,
            actions=actions,
        )

    def execute_plan(
        self,
        plan: ApplyPlan,
        client: HomeAssistantClient,
        git_resources: dict[str, ResourceDocument],
        owner: str = "agent-cli",
    ) -> list[JournalEntry]:
        """Execute an apply plan with locking, read-before-write checks, journaling, and verification."""
        self.acquire_lock(owner=owner, plan_id=plan.plan_id)
        journal: list[JournalEntry] = []

        try:
            baseline = self.load_baseline()
            if baseline is None:
                baseline = BaselineRecord(
                    instance=self.instance,
                    source_commit=plan.git_revision,
                    content_hash=plan.baseline_hash,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    resources={},
                )

            for action in plan.actions:
                rk_str = f"{action.kind}/{action.key}"
                now_str = datetime.now(timezone.utc).isoformat()
                adapter = get_adapter(action.kind)

                # Record start
                entry_start = JournalEntry(
                    plan_id=plan.plan_id,
                    resource=rk_str,
                    action=action.action.value,
                    status="started",
                    timestamp=now_str,
                )
                self.record_journal(entry_start)
                journal.append(entry_start)

                # 1. Read-before-write check
                live_docs = {
                    d.key: adapter.canonicalize(d)
                    for d in adapter.export_from_live(client)
                }
                current_live_doc = live_docs.get(action.key)
                current_live_hash = (
                    canonical_hash(current_live_doc.desired)
                    if current_live_doc and current_live_doc.desired
                    else None
                )

                if current_live_hash != action.expected_live_hash:
                    err_msg = (
                        f"Stale plan refusal on {rk_str}: expected live hash "
                        f"{action.expected_live_hash}, but found {current_live_hash}"
                    )
                    entry_fail = JournalEntry(
                        plan_id=plan.plan_id,
                        resource=rk_str,
                        action=action.action.value,
                        status="failed",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        error=err_msg,
                    )
                    self.record_journal(entry_fail)
                    journal.append(entry_fail)
                    raise StalePlanError(err_msg)

                # 2. Execute mutation
                try:
                    adapter.apply(client, action)
                    entry_applied = JournalEntry(
                        plan_id=plan.plan_id,
                        resource=rk_str,
                        action=action.action.value,
                        status="applied",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    )
                    self.record_journal(entry_applied)
                    journal.append(entry_applied)
                except Exception as exc:
                    entry_fail = JournalEntry(
                        plan_id=plan.plan_id,
                        resource=rk_str,
                        action=action.action.value,
                        status="failed",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        error=str(exc),
                    )
                    self.record_journal(entry_fail)
                    journal.append(entry_fail)
                    raise

                # 3. Readback verification
                if action.action == ActionType.DELETE:
                    # Verify absence
                    post_live_docs = {
                        d.key: d for d in adapter.export_from_live(client)
                    }
                    verified = action.key not in post_live_docs
                else:
                    target_doc = git_resources.get(rk_str)
                    if target_doc is None:
                        target_doc = ResourceDocument(
                            kind=action.kind, key=action.key, desired=action.after
                        )
                    verified = adapter.verify(client, target_doc)

                if not verified:
                    err_msg = f"Readback verification failed on {rk_str}"
                    entry_unverified = JournalEntry(
                        plan_id=plan.plan_id,
                        resource=rk_str,
                        action=action.action.value,
                        status="failed",
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        error=err_msg,
                    )
                    self.record_journal(entry_unverified)
                    journal.append(entry_unverified)
                    raise RuntimeError(err_msg)

                # 4. Advance baseline checkpoint for this verified resource
                if action.action == ActionType.DELETE:
                    baseline.resources.pop(rk_str, None)
                else:
                    norm_desired = adapter.canonicalize(
                        ResourceDocument(
                            kind=action.kind, key=action.key, desired=action.after
                        )
                    ).desired
                    baseline.resources[rk_str] = {
                        "canonical_hash": canonical_hash(norm_desired),
                        "desired": norm_desired,
                        "verified_at": datetime.now(timezone.utc).isoformat(),
                    }
                self.save_baseline(baseline)

                entry_verified = JournalEntry(
                    plan_id=plan.plan_id,
                    resource=rk_str,
                    action=action.action.value,
                    status="verified",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                self.record_journal(entry_verified)
                journal.append(entry_verified)

            return journal

        finally:
            self.release_lock(plan.plan_id)
