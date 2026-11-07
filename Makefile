.PHONY: up down restart logs shell test seed

up:        ; docker compose up -d
down:      ; docker compose down
restart:   ; docker compose restart app-py web
logs:      ; docker compose logs -f --tail=100 app-py
shell:     ; docker compose exec app-py bash
test:      ; docker compose exec -e PYTHONPATH=/app app-py pytest -v
seed:      ; docker compose exec -e PYTHONPATH=/app app-py python3 src/seed.py
