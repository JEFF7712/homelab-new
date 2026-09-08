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
    nixfmt $(git ls-files -co --exclude-standard '*.nix')
    tofu -chdir=tofu/opnsense fmt

fmt-check:
    ruff format --check scripts opnsense_reconciler tests
    nixfmt --check $(git ls-files -co --exclude-standard '*.nix')
    tofu -chdir=tofu/opnsense fmt -check

check-python:
    bash scripts/checks/python.sh

check-nix target="all":
    bash scripts/checks/nix.sh {{target}}

check-gitops:
    bash scripts/checks/gitops.sh

check-registry:
    bash scripts/checks/registry.sh

registry-inventory:
    python -m scripts.registry inventory --output registry/images.inventory.json

registry-resolve:
    python -m scripts.registry resolve --inventory registry/images.inventory.json --output registry/images.lock.json

registry-plan:
    python -m scripts.registry plan --lock registry/images.lock.json

registry-check:
    python -m scripts.registry check --lock registry/images.lock.json

registry-access-control output="artifacts/registry/access-control.json":
    python -m scripts.registry access-control --lock registry/images.lock.json --output {{output}}

registry-copy report="artifacts/registry/import-report.json":
    python -m scripts.registry copy --lock registry/images.lock.json --report {{report}}

registry-verify report="artifacts/registry/verify-report.json":
    python -m scripts.registry verify --lock registry/images.lock.json --report {{report}}

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
