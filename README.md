<h1 align="center">🫚 github-potpie-agno-agent 🫚</h1>
<h2 align="center">An intelligent agent leveraging Agno, Groq, and Potpie to analyze and interact with GitHub repositories.</h2>

<p align="center">
    <img alt="hero" width="450" src="https://emoji-route.deno.dev/svg/🫚" />
</p>

> [!NOTE]
>
> This project provides a sophisticated agent built using the Agno framework. It integrates with the Potpie API to parse and analyze GitHub repositories, leveraging the Groq API for powerful language model capabilities. The agent can answer questions about code, provide repository metrics, analyze trends, and more, all accessible via defined tools and a Streamlit-based playground interface.

## 🌟 Features

> **github-potpie-agno-agent** features intro:

- **Repository Parsing:** Initiate and monitor the parsing of GitHub repositories via the Potpie API.
- **Code Querying:** Ask specific questions about the codebase of a parsed repository.
- **Repository Analysis:** Generate detailed analysis reports including stars, forks, commit frequency, documentation quality, code quality, community engagement, and maintenance status.
- **Trend Analysis:** Retrieve recent trending metrics like star/fork growth rates and contributor activity.
- **Groq Integration:** Utilizes Groq's fast inference capabilities for agent intelligence.
- **Agno Framework:** Built on the robust Agno agent framework for tool definition, state management, and execution.
- **Web Playground:** Includes a simple web interface (`playground.py`) using `agno.playground` to interact with the agent.
- **Environment Configuration:** Uses `.env` files for secure API key management.

## 💻 Installation

> You can install **github-potpie-agno-agent** and its dependencies with one command via:

###### terminal

```bash
# Clone the repository
git clone https://github.com/ArnavK-09/github-potpie-agno-agent.git
cd github-potpie-agno-agent

# Install dependencies (using pip and pyproject.toml)
pip install .

# Or using uv
# uv pip install .

# Set up your .env file with GROQ_API_KEY and POTPIE_API_KEY
# Example .env:
# GROQ_API_KEY=gsk_xxxxxxxxxxxx
# POTPIE_API_KEY=sk_xxxxxxxxxxxx
```

## 📷 Screenshots

| Playground Interface (Example)            |
| ----------------------------------------- |
| ![Demo](https://github.com/ArnavK-09.png) |

---

## 💻 Contributing

> [!TIP]  
> We welcome contributions to improve **github-potpie-agno-agent**! If you have suggestions, bug fixes, or new feature ideas, follow these steps:

1. **Fork the Repository**  
   Click the **Fork** button at the top-right of the repo page.

2. **Clone Your Fork**  
   Clone the repo locally:

   ```bash
   git clone https://github.com/YOUR_USERNAME/github-potpie-agno-agent.git
   ```

3. **Create a Branch**  
   Create a new branch for your changes:

   ```bash
   git checkout -b your-feature-branch
   ```

4. **Make Changes**  
   Implement your changes (bug fixes, features, etc.).

5. **Commit and Push**  
   Commit your changes and push the branch:

   ```bash
   git commit -m "feat(scope): description"
   git push origin your-feature-branch
   ```

6. **Open a Pull Request**  
   Open a PR from your fork to `ArnavK-09/github-potpie-agno-agent` with a detailed description of your changes.

7. **Collaborate and Merge**  
   The maintainers will review your PR, request changes if needed, and merge it once approved.

## 🙋‍♂️ Issues

Found a bug or need help? Please create an issue on the [GitHub repository](https://github.com/ArnavK-09/github-potpie-agno-agent/issues) with a detailed description.

## 👤 Author

<table>
  <tbody>
    <tr>
        <td align="center" valign="top" width="14.28%"><a href="https://github.com/ArnavK-09"><img src="https://github.com/ArnavK-09.png?s=100" width="130px;" alt="Arnav K"/></a><br /><a href="https://github.com/ArnavK-09"><h4><b>Arnav K</b></h4></a></td>
    </tr>
  </tbody>
</table>

---

<h2 align="center">📄 License</h2>

<p align="center">
<strong>github-potpie-agno-agent</strong> is licensed under the <code>MIT</code> License. See the <a href="https://github.com/ArnavK-09/github-potpie-agno-agent/blob/main/LICENSE">LICENSE</a> file for more details (Note: Please add a LICENSE file to the repository).
</p>

---

<p align="center">
    <strong>🌟 If you find this project helpful, please give it a star on GitHub! 🌟</strong>
</p>
