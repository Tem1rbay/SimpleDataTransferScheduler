# YodaAppWebTemplate

Шаблон проекта для веб-приложений

`dotnet new -i Yoda.Templates.V2 --nuget-source https://nuget.servers.lan/nuget/`

<hr>
Для поднятия бд с pgsodium-ом (шифрованием):

`docker run --name PGSODIUM -p 5435:5432 -it -e POSTGRES_PASSWORD=123456  -v C:/pgsodium_getkey.sh:/usr/share/postgresql/16/extension/pgsodium_getkey -d nexus.dc.servers.lan:8084/pg/pgsodium:latest  -c 'shared_preload_libraries=pgsodium'`

где `C:/pgsodium_getkey.sh` :

```bash
#!/bin/bash
KEY_FILE=$PGDATA/pgsodium_root.key

if [ ! -f "$KEY_FILE" ]; then
    head -c 32 /dev/urandom | od -A n -t x1 | tr -d ' \n' > $KEY_FILE
fi
cat $KEY_FILE
```
"# SimpleDataTransferScheduler" 
