# Orchestrator Agent

Sistema serverless de orquestación inteligente de emails mediante IA, desplegado en AWS Lambda. Procesa notificaciones de Microsoft Graph API utilizando Azure OpenAI y herramientas dinámicas MCP.

## Descripción

Agente de IA que automatiza el procesamiento de emails mediante:
- Análisis inteligente del contenido con Azure OpenAI
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
- **IA**: Azure OpenAI, LangChain/LangGraph
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
└── requirements.txt       # Dependencies
```