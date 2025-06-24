/storage/ - This is a library/module
  - Contains the storage abstraction layer
  (interfaces, implementations)
  - Has multiple backends (database, file, memory,
  redis, s3)
  - Contains database models and migrations
  - This is shared code that multiple services can
  import

  /storage-worker/ - This is a microservice
  - A running service that listens to Redis events
  - Handles all write operations to storage
  - Uses the storage library from /storage
  - Has its own Dockerfile for deployment

  Should they be merged? No, they should stay
  separate because:

  1. Different purposes: One is a library, the other
   is a service
  2. Separation of concerns: The storage library can
   be used by other services (API, tests, etc.)
  3. Microservices pattern: Each service directory
  contains just what's needed to run that service
  4. Deployment clarity: Easy to see what gets
  deployed (services have Dockerfiles)