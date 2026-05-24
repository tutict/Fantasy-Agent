ARG ES_VERSION=9.2.6
FROM elasticsearch:${ES_VERSION}

ARG ES_VERSION
ARG IK_PLUGIN_VERSION
ARG PINYIN_PLUGIN_VERSION

RUN set -eux; \
    ik_version="${IK_PLUGIN_VERSION:-$ES_VERSION}"; \
    pinyin_version="${PINYIN_PLUGIN_VERSION:-$ES_VERSION}"; \
    bin/elasticsearch-plugin install --batch "https://get.infini.cloud/elasticsearch/analysis-ik/${ik_version}"; \
    bin/elasticsearch-plugin install --batch "https://get.infini.cloud/elasticsearch/analysis-pinyin/${pinyin_version}"
