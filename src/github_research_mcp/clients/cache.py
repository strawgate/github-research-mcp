from github_research_mcp.clients.elasticsearch import get_elasticsearch_client
from github_research_mcp.vendored.caching import CacheProtocol, InMemoryCache
from github_research_mcp.vendored.elasticsearch_cache import ElasticsearchCache


def get_cache_backend() -> CacheProtocol:
    if elasticsearch_client := get_elasticsearch_client():
        return ElasticsearchCache(elasticsearch_client=elasticsearch_client)

    return InMemoryCache()
