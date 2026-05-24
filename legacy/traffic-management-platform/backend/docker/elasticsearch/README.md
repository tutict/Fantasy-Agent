# Elasticsearch 9 plugin image

Build the local Elasticsearch image with IK and Pinyin plugins:

```powershell
docker build -t final-assignment-elasticsearch:9.2.6 `
  --build-arg ES_VERSION=9.2.6 `
  .\backend\docker\elasticsearch
```

If a plugin release uses a different version number than Elasticsearch itself, override it explicitly:

```powershell
docker build -t final-assignment-elasticsearch:9.2.6 `
  --build-arg ES_VERSION=9.2.6 `
  --build-arg IK_PLUGIN_VERSION=9.2.6 `
  --build-arg PINYIN_PLUGIN_VERSION=9.2.6 `
  .\backend\docker\elasticsearch
```

The backend defaults to this image tag unless `APP_DOCKER_ELASTICSEARCH_IMAGE` or `spring.elasticsearch.uris` is provided.

The Dockerfile uses the `elasticsearch:${ES_VERSION}` base image from Docker Hub to avoid the slower `docker.elastic.co` registry path during local development.
