# Agent workflow state

## Problem

An interrupted or concurrent agent workflow needs a durable, local record of its
objective, ownership boundaries, checkpoint, outstanding work, and validation
evidence. The record must not turn malformed input, a competing writer, or an
interrupted replacement into lost state.

## Decision

Store each task at `.agent-state/tasks/<task-id>/task.json`. Records use schema
version 1 and a monotonically increasing integer revision. A checkpoint caller
submits the complete record and the revision it read. The update succeeds only
when that expected revision still matches.

Writes acquire an exclusive per-task lock, write a fully validated temporary
file in the task directory, flush and fsync it, replace `task.json`, and fsync
the directory. The lock records its owner PID, session, timestamp, and token;
cleanup removes a lock only when its token still belongs to the caller.

Checkpoint state describes the checkout observed when the record was saved.
Resume inspects the current checkout and reports base availability and drift.
It derives stale verification flags in its returned result, without changing
the saved task record.

## Rationale

Task state is a local recovery aid, so it belongs beside the checkout and is
not a shared infrastructure control plane. Compare-and-swap revisions make a
lost update visible to the writer. A same-directory atomic replacement retains
the previously valid record when input validation or replacement fails.

## Alternatives considered

Keeping one mutable repository-wide task file would make independent task
writes contend unnecessarily. Appending unchecked checkpoints would preserve
history but leave consumers to select a valid current state. Relying on an
in-memory session loses the recovery record on interruption. Automatically
rewriting stale flags during resume would make an inspection command mutate
state and conceal when verification became stale.

## Consequences

Operators must reload after a revision conflict and provide the whole,
validated checkpoint document. A stale lock is a visible conflict that needs
operator recovery rather than implicit deletion. The repository ignores local
state, so a task record does not transfer with a commit; durable records and
evidence references must be stored through their owning systems.

## Superseding record semantics

A higher record revision supersedes the same task's earlier revision only
after the replacement has completed. The prior on-disk record remains the
authoritative record if validation, locking, or replacement fails. Schema
versions are explicit so future readers can reject records they do not
understand instead of guessing at their meaning.
