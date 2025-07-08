#with celery

docker compose -f docker-compose.yml -f docker-compose.celery.yml build $(docker compose -f docker-compose.yml -f docker-compose.celery.yml config --services | grep -v crucible-frontend)

docker compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.celery.yml up

#without celery
docker compose -f docker-compose.yml build $(docker compose -f docker-compose.yml config --services | grep -v crucible-frontend)

docker compose -f docker-compose.yml -f docker-compose.dev.yml up

#build once
docker compose -f docker-compose.yml -f docker-compose.dev.yml build crucible-frontend