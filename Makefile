up:
	docker compose -p alpha -f docker-compose.yml build && docker compose -p alpha -f docker-compose.yml up -d

down:
	docker compose -p alpha -f docker-compose.yml down

web-wsgi-rebuild:
	docker compose -p alpha -f docker-compose.yml build django_wsgi --no-cache
	docker compose -p alpha -f docker-compose.yml up -d django_wsgi

celery-rebuild:
	docker compose -p alpha -f docker-compose.yml build celery --no-cache
	docker compose -p alpha -f docker-compose.yml up -d celery

celery-beat-rebuild:
	docker compose -p alpha -f docker-compose.yml build celery-beat --no-cache
	docker compose -p alpha -f docker-compose.yml up -d celery-beat
