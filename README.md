# Orchestrator Agent

Sistema serverless de orquestación inteligente de emails mediante IA, desplegado en AWS Lambda. Procesa notificaciones de Microsoft Graph API utilizando Azure OpenAI y herramientas dinámicas MCP.

## Descripción

Agente de IA que automatiza el procesamiento de emails mediante:
- Análisis inteligente del contenido con Azure OpenAI (GPT-4)
- Ejecución de acciones automáticas (clasificación, enrutamiento, respuestas)
- Integración con Microsoft Graph API vía webhooks
- Sistema extensible de herramientas mediante MCP (Model Context Protocol)

## Arquitectura

```
Microsoft Graph API → API Gateway → AWS Lambda
                                        ↓
                                  LangGraph Agent
                                        ↓
                            Análisis → Decisión → Acción
                                        ↓
                                 Herramientas MCP
```

## Stack Tecnológico

- **Runtime**: Python 3.12, AWS Lambda
- **IA**: Azure OpenAI (GPT-4), LangChain/LangGraph
- **Integraciones**: Microsoft Graph API, MCP
- **Arquitectura**: Serverless, Event-driven

## Estructura del Proyecto

```
orchestrator_agent/
├── handler.py              # Entry point AWS Lambda
├── src/
│   ├── graph.py           # Workflow LangGraph
│   ├── state.py           # State schema
│   └── tool_loader.py     # MCP tools manager
├── interactive_test.py    # Interactive testing
├── local_test_runner.py   # Local Lambda simulation
└── requirements.txt       # Dependencies
```

## Configuración

### Variables de Entorno

Crear archivo `.env` con:

```env
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-08-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4
MCP_SERVERS_CONFIG={"server_name": {"url": "http://mcp-server:8000"}}
```

### Instalación

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env  # Editar con tus credenciales
```

## Uso

### Producción
Desplegado como AWS Lambda, procesa automáticamente webhooks de Microsoft Graph API.

### Testing Local

```bash
# Modo interactivo
python interactive_test.py

# Simulación Lambda
python local_test_runner.py

# Test con mensaje específico
python interactive_test.py "Procesa email ID 12345"
```

## Deployment

### AWS Lambda

1. Empaquetar proyecto con dependencias
2. Crear función Lambda (Python 3.12, timeout mínimo 60s)
3. Configurar variables de entorno
4. Vincular API Gateway como trigger
5. Registrar webhook URL en Microsoft Graph

### Configuración MCP

Las herramientas se definen en `MCP_SERVERS_CONFIG`:

```json
{
  "email_tools": {"url": "http://email-server:8000"},
  "classifier": {"url": "http://ml-classifier:8000"}
}
```

## Arquitectura del Grafo LangGraph

El workflow implementa un grafo cíclico con 2 nodos:

```
┌─────────────────────────────────────────┐
│          Entry Point: "agent"           │
└──────────────┬──────────────────────────┘
               │
               ▼
        ┌─────────────┐
        │    agent    │ ← Nodo principal (LLM reasoning)
        │   (async)   │
        └──────┬──────┘
               │
        ┌──────▼──────────┐
        │ should_continue │ ← Conditional edge
        └──┬──────────┬───┘
           │          │
    ¿Tool calls?    No
           │          │
           ▼          ▼
     ┌─────────┐   END
     │  tools  │
     └────┬────┘
          │
          └──► Regresa a "agent" (loop)
```

### Nodos del Grafo

**1. Nodo "agent"** ([src/graph.py:22-43](src/graph.py#L22-L43))
- Ejecuta `agent_node()` (función async)
- Invoca Azure OpenAI GPT-4 con `model.ainvoke()`
- Filtra mensajes huérfanos (ToolMessages sin tool_call previo)
- Retorna respuesta del LLM con posibles tool_calls

**2. Nodo "tools"** ([src/graph.py:12](src/graph.py#L12))
- Ejecuta `ToolNode(tools)` de LangGraph
- Ejecuta las herramientas MCP solicitadas por el agente
- Retorna resultados como ToolMessages

### Edges del Grafo

**Entry Point**: `"agent"` - Primera ejecución comienza en el nodo agent

**Conditional Edge**: `agent → should_continue()` ([src/graph.py:45-52](src/graph.py#L45-L52))
- Si el último mensaje tiene `tool_calls`: → `"tools"`
- Si no hay `tool_calls`: → `END`

**Fixed Edge**: `tools → agent` - Siempre regresa al agente después de ejecutar tools

## Componentes Clave

**[handler.py](handler.py)** - Lambda handler, procesa eventos Graph API
**[src/graph.py](src/graph.py)** - Workflow ReAct con StateGraph de LangGraph
**[src/tool_loader.py](src/tool_loader.py)** - Carga dinámica de herramientas MCP
**[src/state.py](src/state.py)** - Schema de estado del agente (AgentState)

## Troubleshooting

| Error | Solución |
|-------|----------|
| `AZURE_OPENAI_API_KEY no encontrada` | Verificar archivo `.env` |
| `No tools loaded` | Validar `MCP_SERVERS_CONFIG` y conectividad |
| Lambda timeout | Aumentar timeout a 60+ segundos |

## Desarrollo

```bash
# Testing interactivo
python interactive_test.py

# Añadir nueva herramienta MCP
# 1. Configurar en MCP_SERVERS_CONFIG
# 2. El sistema la descubrirá automáticamente
```
