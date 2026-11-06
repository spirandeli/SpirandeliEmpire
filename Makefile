.PHONY: bootstrap up down restart logs shell migrate fresh tinker worker-status

bootstrap: ; ./scripts/bootstrap.sh
up:        ; docker compose up -d
down:      ; docker compose down
restart:   ; docker compose restart app worker
logs:      ; docker compose logs -f --tail=100 app worker
shell:     ; docker compose exec -u www-data app bash
migrate:   ; docker compose exec -u www-data app php artisan migrate
fresh:     ; docker compose exec -u www-data app php artisan migrate:fresh
tinker:    ; docker compose exec -u www-data -e HOME=/tmp app php artisan tinker
worker-status: ; docker compose exec worker supervisorctl -c /etc/supervisor/supervisord.conf status
