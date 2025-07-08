# Docker Compose Production Fixes

## Issues Fixed

1. **Duplicate security_opt entries**
   - `storage-service` had `no-new-privileges:true` in both files
   - `crucible-frontend` had duplicate security options
   - `executor-1` had duplicate `no-new-privileges:true`

2. **Removed legacy services**
   - Removed `queue` and `queue-worker` from prod overrides
   - These services were removed from main compose but still in prod

3. **Added busybox overrides**
   - `base` and `executor-ml-image` now use `busybox:latest`
   - Prevents "pull access denied" warnings in production

4. **Removed obsolete version**
   - Removed `version: '3.8'` as it's deprecated

## Validation

Files now validate successfully:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet
```

## Deployment

Copy both files to EC2:
```bash
scp docker-compose.yml docker-compose.prod.yml ubuntu@<EC2_IP>:~/crucible/
```

Pull without warnings:
```bash
sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
```