# YT_ELT

Local learning environment: Windows PowerShell, Podman, and the existing WSL2
`astro-machine`. The root `docker-compose.yaml` follows the course's Airflow 2.9.2
stack and uses Airflow UI port **8081** and PostgreSQL host port **5433**.
The mount-preparation helper under `docker/` handles the commas in this Windows
project path through a Linux symlink; the command guide explains it.

- [Docker Compose explained](Markdowns/Docker/Docker_Compose_Lecture_Explained.md)
- [PostgreSQL initialization script explained](Markdowns/Docker/Postgres_Initialization_Script_Explained.md)
- [Docker and Podman commands](Markdowns/Docker/Docker_and_Podman_Commands_Guide.md)
- [PostgreSQL commands and interactions](Markdowns/Docker/Postgres_Commands_and_Interactions.md)
- [Soda data quality: overview, examples, and commands](Markdowns/Testing/Soda_Data_Quality_Overview_and_Commands.md)

Read the command guide before startup. Keep `.env` private and use `.env.example`
only as a template. Normal shutdown preserves database storage; deleting the
named volume erases all three databases. This is a historical course environment
for local learning.
