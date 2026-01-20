# Oracle AI Developer Hub

This repository contains technical resources to help AI Developers build AI applications, agents, and systems using Oracle AI Database and OCI services alongside other key components of the AI/Agent stack.

## What You'll Find

This repository is organized into several key areas:

### 📱 **Apps** (`/apps`)

Applications and reference implementations demonstrating how to build AI-powered solutions with Oracle technologies. These complete, working examples showcase end-to-end implementations of AI applications, agents, and systems that leverage Oracle AI Database and OCI services. Each application includes source code, deployment configurations, and documentation to help developers understand architectural patterns, integration approaches, and best practices for building production-grade AI solutions.

| Name                     | Description                                                                                                                      | Link                                                                                                           |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| agentic_rag              | Intelligent RAG system with multi-agent Chain of Thought (CoT), PDF/Web/Repo processing, and Oracle AI Database 26ai integration | [![View App](https://img.shields.io/badge/View%20App-blue?style=flat-square)](./apps/agentic_rag)              |
| oci-generative-ai-jet-ui | Full-stack AI application with Oracle JET UI, OCI Generative AI integration, Kubernetes deployment, and Terraform infrastructure | [![View App](https://img.shields.io/badge/View%20App-blue?style=flat-square)](./apps/oci-generative-ai-jet-ui) |

### 📓 **Notebooks** (`/notebooks`)

Jupyter notebooks and interactive tutorials covering:

- AI/ML model development and experimentation
- Oracle Database AI features and capabilities
- OCI AI services integration patterns
- Data preparation and analysis workflows
- Agent development and orchestration examples

| Name                              | Description                                                      | Stack                                         | Link                                                                                                                                           |
| --------------------------------- | ---------------------------------------------------------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| memory_context_engineering_agents | Build AI agents with 6 types of persistent memory.               | LangChain, Oracle AI Database, OpenAI, Tavily | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./notebooks/memory_context_engineering_agents.ipynb) |
| oracle_rag_agents_zero_to_hero    | Learn to build RAG agents from scratch using Oracle AI Database. | Oracle AI Database, OpenAI, OpenAI Agents SDK | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./notebooks/oracle_rag_agents_zero_to_hero.ipynb)    |
| oracle_rag_with_evals             | Build RAG systems with comprehensive evaluation metrics          | Oracle AI Database, OpenAI, BEIR, Galileo     | [![Open Notebook](https://img.shields.io/badge/Open%20Notebook-orange?style=flat-square)](./notebooks/oracle_rag_with_evals.ipynb)             |

### 🎓 **Workshops** (`/workshops`)

Hands-on workshops and guided learning experiences:

- Step-by-step tutorials for building AI applications
- End-to-end project walkthroughs
- Best practices and architectural patterns
- Integration guides for Oracle AI Database and OCI services

| Name          | Description                  | Link |
| ------------- | ---------------------------- | ---- |
| _Coming soon_ | Workshops will be added here | -    |

### 📚 **Guides** (`/guides`)

Comprehensive documentation and reference materials:

- Architecture patterns and design guides
- API documentation and integration examples
- Deployment and operations guides
- Troubleshooting and optimization tips
- Security and compliance best practices

| Name          | Description               | Link |
| ------------- | ------------------------- | ---- |
| _Coming soon_ | Guides will be added here | -    |

### 🤝 **Partners** (`/partners`)

Notebooks and apps contributed by partners in the AI ecosystem. AI Developers can use these resources to understand how to use Oracle AI Database and OCI alongside tools such as LangChain, Galileo, LlamaIndex, and other popular AI/ML frameworks and platforms.

| Name          | Description                                      | Stack | Link |
| ------------- | ------------------------------------------------ | ----- | ---- |
| _Coming soon_ | Partner-contributed resources will be added here | -     | -    |

## Getting Started

1. **Explore Applications**: Start with the applications in `/apps` to see complete, working examples
2. **Follow Workshops**: Check `/workshops` for guided learning paths
3. **Experiment with Notebooks**: Use `/notebooks` for hands-on experimentation
4. **Reference Guides**: Consult `/guides` for detailed documentation
5. **Check Partner Resources**: Explore `/partners` for integrations with popular AI tools and frameworks

## Contributing

This project is open source. Please submit your contributions by forking this repository and submitting a pull request! Oracle appreciates any contributions that are made by the open-source community.

### Development Setup

Before contributing, please set up pre-commit hooks to ensure code is automatically formatted:

1. **Install pre-commit**:

   ```bash
   pip install pre-commit
   ```

2. **Install additional dependencies** (optional, includes pre-commit and ruff):

   ```bash
   pip install -r requirements-dev.txt
   ```

3. **Install pre-commit hooks**:

   ```bash
   pre-commit install
   ```

4. **Optional: Format existing code**:
   ```bash
   pre-commit run --all-files
   ```

The pre-commit hooks will automatically format your code using:

- **Ruff** for Python files (formatting and linting)
- **Prettier** for JavaScript, TypeScript, JSON, YAML, and Markdown files

For more detailed information, see [SETUP_PRE_COMMIT.md](./SETUP_PRE_COMMIT.md).

## License

Copyright (c) 2024 Oracle and/or its affiliates.

Licensed under the Universal Permissive License (UPL), Version 1.0.

See [LICENSE](LICENSE) for more details.

ORACLE AND ITS AFFILIATES DO NOT PROVIDE ANY WARRANTY WHATSOEVER, EXPRESS OR IMPLIED, FOR ANY SOFTWARE, MATERIAL OR CONTENT OF ANY KIND CONTAINED OR PRODUCED WITHIN THIS REPOSITORY, AND IN PARTICULAR SPECIFICALLY DISCLAIM ANY AND ALL IMPLIED WARRANTIES OF TITLE, NON-INFRINGEMENT, MERCHANTABILITY, AND FITNESS FOR A PARTICULAR PURPOSE. FURTHERMORE, ORACLE AND ITS AFFILIATES DO NOT REPRESENT THAT ANY CUSTOMARY SECURITY REVIEW HAS BEEN PERFORMED WITH RESPECT TO ANY SOFTWARE, MATERIAL OR CONTENT CONTAINED OR PRODUCED WITHIN THIS REPOSITORY. IN ADDITION, AND WITHOUT LIMITING THE FOREGOING, THIRD PARTIES MAY HAVE POSTED SOFTWARE, MATERIAL OR CONTENT TO THIS REPOSITORY WITHOUT ANY REVIEW. USE AT YOUR OWN RISK.

---

**Note**: This repository is actively maintained and updated with new resources, examples, and best practices for Oracle AI development.
