agent-context *args:
    python -m scripts.agent context {{args}}

doctor *args:
    python -m scripts.agent doctor {{args}}

check-changed *args:
    python -m scripts.agent check-changed {{args}}

check:
    python -m scripts.agent check

fmt:
    python -m scripts.agent fmt

fmt-check:
    python -m scripts.agent fmt-check

task-new id *args:
    python -m scripts.agent task-new {{id}} {{args}}

task-resume id *args:
    python -m scripts.agent task-resume {{id}} {{args}}

task-checkpoint id *args:
    python -m scripts.agent task-checkpoint {{id}} {{args}}

task-export id *args:
    python -m scripts.agent task-export {{id}} {{args}}

status target *args:
    python -m scripts.agent status {{target}} {{args}}
