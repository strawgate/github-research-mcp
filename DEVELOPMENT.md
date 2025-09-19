
# Project Structure

```
src/github_research_mcp/
├── main.py                    # Main MCP server entry point
├── public.py                  # Public repository server entry point
├── clients/
│   └── github.py              # GitHub API client with token management
├── models/
│   ├── graphql/
│   │   ├── fragments.py       # GraphQL fragments for issues, PRs, comments
│   │   └── queries.py         # GraphQL query definitions
│   ├── query/
│   │   ├── base.py            # Base query qualifiers and operators
│   │   ├── code.py            # Code search query builders
│   │   └── issue_or_pull_request.py  # Issue/PR search query builders
│   ├── repository/
│   │   └── tree.py            # Repository tree and file analysis models
│   └── rest/
│       └── models.py          # REST API response models
├── sampling/
│   ├── extract.py             # Structured data extraction utilities
│   └── prompts.py             # AI prompt building and management
└── servers/
    ├── base.py                # Base server with common functionality
    ├── public.py              # Public repository server
    ├── repository.py          # Repository analysis server
    ├── issues_or_pull_requests.py  # Issue/PR research server
    └── shared/
        ├── annotations.py     # Type annotations and field definitions
        └── utility.py         # Shared utility functions
```

# Key Dependencies

- **fastmcp**: MCP server framework with sampling support
- **githubkit**: GitHub API client with GraphQL and REST support
- **openai**: AI model integration for summarization
- **pydantic**: Data validation and serialization
- **asyncclick**: CLI framework for command-line interface
- **async-lru**: LRU caching for performance optimization
- **yaml**: YAML processing for prompt configuration

# Architecture

## Server Types

The project provides two distinct MCP servers:

1. **Main Server** (`main.py`): Full-featured server with repository analysis, issue/PR research, and AI summarization
2. **Public Server** (`public.py`): Specialized server for public repositories with star count filtering and rate limiting

## Key Components

**Query System**: Sophisticated query builder supporting:
- Multiple qualifier types (keywords, labels, authors, states, etc.)
- Boolean operators (AND/OR) for complex queries
- Advanced filtering for both code and issue/PR searches

**AI Integration**: 
- Structured data extraction from AI responses
- Flexible prompt building system
- Support for multiple AI models and configurations

**Data Models**:
- Comprehensive GraphQL fragments for GitHub data
- Pydantic models for type safety and validation
- Repository tree analysis and file type statistics

**Caching & Performance**:
- LRU caching for frequently accessed data
- Token estimation for AI model optimization
- Efficient GraphQL query construction

The public server also leverages a distributed cache via Elasticsearch to cache responses.