agent-context *args:
    python -m scripts.agent context {{args}}

doctor *args:
    python -m scripts.agent doctor {{args}}

check-changed *args:
    python -m scripts.agent check-changed {{args}}

check:
    bash scripts/checks/all.sh

fmt:
    ruff format scripts opnsense_reconciler tests
    nixfmt $(git ls-files '*.nix')
    tofu -chdir=tofu/opnsense fmt

fmt-check:
    ruff format --check scripts opnsense_reconciler tests
    nixfmt --check $(git ls-files '*.nix')
    tofu -chdir=tofu/opnsense fmt -check

check-python:
    bash scripts/checks/python.sh

check-nix target="all":
    bash scripts/checks/nix.sh {{target}}

check-gitops:
    bash scripts/checks/gitops.sh

check-tofu:
    bash scripts/checks/tofu.sh

check-docs:
    python scripts/checks/docs.py

provision-check-deps:
    tofu -chdir=tofu/opnsense init -backend=false

refresh-crd-schemas:
    python scripts/checks/provision_schemas.py

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
