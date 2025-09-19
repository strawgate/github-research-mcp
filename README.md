# GitHub Research MCP and Agents.md Generator

A Model Context Protocol (MCP) server for researching GitHub repositories, issues, and pull requests with sampling-powered analysis and summarization capabilities.

## Agents.md Generator

The Agents.md Generator is a free & public MCP Server that generates AGENTS.md files for public GitHub repositories that have at least 10 stars. The Agents.md generator is powered by the GitHub Research MCP and leverages the repo summarization tool to generate the AGENTS.md file.

Try it out!

| IDE | Command | 
| --- | --- |
| Cursor | [Add it to Cursor](cursor://anysphere.cursor-deeplink/mcp/install?name=github-research-mcp-public&config=eyJ1cmwiOiJodHRwczovL2dpdGh1Yi1yZXNlYXJjaC1tY3AtcHVibGljLmZhc3RtY3AuYXBwL21jcCJ9) |
| Gemini CLI | `gemini mcp add github-research-mcp-public https://github-research-mcp-public.fastmcp.app/mcp --transport http` |
| Claude Desktop | [Download manifest](https://github-research-mcp-public.fastmcp.app/manifest.dxt?v=9320d032-0eee-4025-bbe0-302556c54280) |
| Claude Code | `claude mcp add --scope local --transport http github-research-mcp-public https://github-research-mcp-public.fastmcp.app/mcp`

## Features

### Repository Analysis
- **File Discovery**: Browse repository structure and find files by patterns
- **Code Search**: Search for code across repositories with advanced filtering
- **File Analysis**: Get file contents, README files, and file extension statistics
- **Repository Summarization**: AI-powered analysis of entire repositories

### Issue & Pull Request Research
- **Detailed Research**: Get comprehensive information about specific issues and pull requests
- **Advanced Search**: Search issues/PRs by keywords, labels, authors, and more
- **Timeline Analysis**: Track related issues, PRs, and cross-references
- **Comment Analysis**: Review all comments and discussion threads

### AI-Powered Analysis
- **Intelligent Summarization**: Generate focused summaries using Google Gemini by default (OpenAI optional)
- **Context-Aware Research**: AI-driven analysis of complex GitHub data
- **Flexible Prompting**: Customizable prompts for different analysis needs
- **Structured Data Extraction**: Convert unstructured GitHub data into structured formats

### Technical Features
- **GraphQL Integration**: Efficient data fetching using GitHub's GraphQL API
- **REST API Support**: Fallback to REST API for broader compatibility
- **Rate Limiting**: Built-in rate limiting and request management
- **Flexible Configuration**: Support for both stdio and HTTP transports
- **Public Repository Support**: Specialized tools for public repository analysis

## Self Hosting GitHub Research MCP

To run the server as a stdio MCP Server, use the following command:
```bash
uvx github-research-mcp
```

To run the server as a HTTP MCP Server, use the following command:
```bash
uvx github-research-mcp --mcp-transport streamable-http
```

Note: To disable AI-powered analysis, set `DISABLE_SAMPLING=true`.

### Environment Variables

**Required:**
- `GITHUB_TOKEN` or `GITHUB_PERSONAL_ACCESS_TOKEN`: Required for GitHub API access

**Sampling Fallback:**
For clients that dont support sampling, you can provide an API key for either Google or OpenAI to enable sampling fallback -- where the server performs an AI call to generate the response instead of relying on the client's sampling capabilities.

- Google AI (default):
  - `GOOGLE_API_KEY`: Required to enable summarization and research tools
  - `GOOGLE_MODEL`: Gemini model to use (default: `gemini-2.5-flash`)
- OpenAI (optional alternative):
  - `OPENAI_API_KEY`: If using OpenAI with a compatible sampling handler
  - `OPENAI_MODEL`: OpenAI model (e.g., `gpt-4o`) if using OpenAI
  - `OPENAI_BASE_URL`: Custom OpenAI API base URL (optional)
- Control:
  - `DISABLE_SAMPLING`: Set to `true` to disable AI summarization/research tools

**Public Repository Features:**
- `MINIMUM_STARS`: Minimum star count for repository summarization (default: 10)
- `OWNER_ALLOWLIST`: Comma-separated list of owners to allow regardless of star count

### Available Tools

The server provides multiple tool categories:

**Repository Tools** (always available):
- `get_files`: Browse repository file structure
- `find_files`: Search for files by patterns
- `search_files`: Advanced file search with filtering
- `get_readmes`: Retrieve README files
- `get_file_extensions`: Analyze file type distribution

**Issue & Pull Request Tools** (always available):
- `get_issue_or_pull_request`: Get detailed information about specific issues/PRs
- `search_issues_or_pull_requests`: Search issues/PRs with advanced filtering

**Sampling-Powered Tools** (requires Sampling or Sampling Fallback configuration):
- `summarize`: Generate AI-powered repository summaries
- `research_issue_or_pull_request`: AI-driven analysis of issues/PRs

## MCP Client Configuration

### VS Code

1. Open the command palette (Ctrl+Shift+P or Cmd+Shift+P).
2. Type "Settings" and select "Preferences: Open User Settings (JSON)".
3. Add the following MCP Server configuration:

```json
{
  "mcp": {
    "servers": {
      "GitHub Research MCP": {
        "command": "uvx",
        "args": [
          "github-research-mcp",
        ],
        "env": {
          "GITHUB_TOKEN": "your_github_token_here",
        }
      }
    }
  }
}
```

### Cline / Roo Code

Add the following to your MCP Server configuration:

```json
{
  "GitHub Research MCP": {
    "command": "uvx",
    "args": [
      "github-research-mcp",
    ],
    "env": {
      "GITHUB_TOKEN": "your_github_token_here",
    }
  }
}
```

### Example Usage

Once configured, you can use the tools for comprehensive GitHub research:

**Repository Analysis:**
- **Browse files**: Explore repository structure and find specific files
- **Code search**: Search for functions, classes, or patterns across the codebase
- **File analysis**: Get file contents and analyze file type distribution
- **Repository summaries**: Get AI-powered analysis of entire repositories

**Issue & Pull Request Research:**
- **Research specific items**: Get detailed information about issue #123 or PR #456
- **Advanced search**: Find issues/PRs by keywords, labels, authors, or states
- **Timeline analysis**: Track related issues, PRs, and cross-references
- **AI analysis**: Get intelligent summaries and insights about issues/PRs

**Public Repository Research:**
- **Public repo summaries**: Analyze public repositories with star count filtering
- **Owner allowlisting**: Bypass star requirements for specific organizations

## Development & Testing

### Running Tests

```bash
# Install development dependencies
uv sync --group dev

# Required test environment
export GITHUB_TOKEN=...           # required
export GOOGLE_API_KEY=...         # required for sampling tests
export MODEL=gemini-2.5-flash     # optional (default)

# Run tests
pytest

# Run with coverage
pytest --cov=github_research_mcp
```

### Project Structure

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

### Key Dependencies

- **fastmcp**: MCP server framework with sampling support
- **githubkit**: GitHub API client with GraphQL and REST support
- **openai**: AI model integration for summarization
- **pydantic**: Data validation and serialization
- **asyncclick**: CLI framework for command-line interface
- **async-lru**: LRU caching for performance optimization
- **yaml**: YAML processing for prompt configuration

## Architecture

### Server Types

The project provides two distinct MCP servers:

1. **Main Server** (`main.py`): Full-featured server with repository analysis, issue/PR research, and AI summarization
2. **Public Server** (`public.py`): Specialized server for public repositories with star count filtering and rate limiting

### Key Components

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

## License

See [LICENSE](LICENSE).