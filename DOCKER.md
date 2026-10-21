### Database location
By default, the SQLite database is stored in `./data/dictionary.db` on
your host, which persists across container restarts. To use MSSQL or
PostgreSQL instead, set `DATABASE_URL`:

```yaml
services:
  data-dictionary:
    environment:
      - DATABASE_URL=mssql+pymssql://<username>:<password>@sqlserver:1433/data_dictionary
      # or: postgresql+psycopg2://<username>:<password>@postgres:5432/data_dictionary
```
