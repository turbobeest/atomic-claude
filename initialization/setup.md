# WeatherWise Configuration

**name**: WeatherWise
**description**: A weather forecasting application that provides real-time weather data and forecasts
**type**: webapp
**primary_goal**: Build a responsive weather app with location-based forecasts and interactive UI

## LLM Configuration
**llm.primary_provider**: aws-bedrock
**llm.primary_model**: null
**llm.fast_model**: null
**llm.local_fallback**: true

## Provider Configuration
**providers.chains.global**: aws-bedrock ollama

## Repository
**repository.url**: https://github.com/turbobeest/atomic-claude.git
**repository.default_branch**: main
**repository.pr_strategy**: feature-branch
**repository.commit_strategy**: per-task
**repository.push_strategy**: auto
**repository.commit_format**: conventional

## Sandbox
**sandbox.command_approval_mode**: cautious
**sandbox.network_mode**: cui
**sandbox.network_access**: fetch-only
**sandbox.forbidden_paths**: [".env*", "secrets/", "*.key", "*.pem"]
**sandbox.blocked_ips**: ["169.254.169.254/32"]

## Pipeline
**pipeline.mode**: component
**pipeline.skip_phases**: []
**pipeline.human_gates**: [0]

## Agents
**agents.phase_0**: default
**agents.phase_1**: infer

## Tech Stack
**tech_stack**: ["TypeScript", "React", "Node.js", "Express", "OpenWeather API"]
**frameworks**: ["Next.js", "Tailwind CSS"]

## Constraints
**constraints.technical**: ["Modern web standards", "Responsive design", "API rate limiting"]
**constraints.infrastructure**: Deployed as static site with API backend
