# Usage Boundaries

## `claude-tech-squad`

Use this plugin as the execution layer.

It is responsible for:

- discovery and blueprinting
- specialist orchestration
- coordinated implementation
- QA, review, documentation, and release closure

## `claude-config`

Use `claude-config` as the environment layer.

It is responsible for:

- global defaults
- reusable commands, skills, and rules
- portable templates and helper agents

## Practical Rule

- if you are setting up the machine or baseline, use `claude-config`
- if you are delivering a feature or initiative in a repository, use `claude-tech-squad`
