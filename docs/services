services
	frontend
		uses openapi-to-typescript
			openapi.yaml -> types.ts
	api
		current goal
			updates openapi.yaml on every fastapi server start

goal
	api publishes its api contract to openapi.yaml which other services -- especially frontend -- can use to ensure they're referencing the correct api structure
issue
		in docker, this requires writing a file to disk, but otherwise the image is read only which is highly desirable for security considerations
solutions
	attempt to fix current design
		need to change to write
	alternative designs
		docker volume
		frontend interacts with api server during build