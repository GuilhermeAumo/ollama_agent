# Ollama Coding Agent

A ollama based coding agent for local development.

## Instalation
First, install the ollama client: https://ollama.com/download
```
conda create -n ollama-agent python=3.11
conda activate ollama-agent
pip install ollama
```

Configure ollama model. This is needed to increas ollama context length (change model name in the command below and in Modelfile to use a different model):
```
ollama pull qwen3:8b
ollama create -f Modelfile qwen3:custom
```

Then, run the agent on the command line on the folder you wish to use it:
```
python /path/to/ollama_agent/ollama_agent.py
```