@echo off
docker start elasticsearch >nul 2>&1
if %errorlevel% neq 0 (
    docker run -d --name elasticsearch -p 9200:9200 -p 9300:9300 -e discovery.type=single-node docker.elastic.co/elasticsearch/elasticsearch:9.0.3
) else (
    echo Elasticsearch container started
)
