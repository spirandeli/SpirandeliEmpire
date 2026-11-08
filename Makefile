.PHONY: up down restart logs shell test seed cli automations optimize deploy

up:        ; docker compose up -d
down:      ; docker compose down
restart:   ; docker compose restart app-py web
logs:      ; docker compose logs -f --tail=100 app-py
shell:     ; docker compose exec app-py bash
test:      ; docker compose exec -e PYTHONPATH=/app app-py pytest -v
seed:      ; docker compose exec -e PYTHONPATH=/app app-py python3 -m src.cli seed
cli:       ; docker compose exec -e PYTHONPATH=/app app-py python3 -m src.cli
automations: ; docker compose exec -e PYTHONPATH=/app app-py python3 -m src.cli run-automations --force
optimize:  ; docker compose exec -e PYTHONPATH=/app app-py python3 -m src.cli optimize-growth
deploy:    ; python3 scripts/deploy_remote.py
