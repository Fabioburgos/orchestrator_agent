# interactive_test.py

import asyncio
from handler import app
from src.state import AgentState
from langchain_core.messages import HumanMessage

async def test_orchestrator(user_message: str):
    """
    Envía un mensaje al orquestador y muestra el resultado.
    
    Args:
        user_message: El mensaje o comando del usuario
    """
    print("\n" + "="*70)
    print(f"MENSAJE DEL USUARIO: {user_message}")
    print("="*70)
    
    # Crear el estado inicial con el mensaje del usuario
    initial_state: AgentState = {
        "messages": [HumanMessage(content = user_message)],
        "message_id": "test-interactive",
        "original_notification": {}
    }
    
    print("\nInvocando el orquestador...")
    
    try:
        final_state = await app.ainvoke(initial_state) # Invocar el grafo
        
        print("\nHISTORIAL DE EJECUCIÓN:")
        print("-" * 70)
        
        for i, msg in enumerate(final_state["messages"], 1):
            msg_type = type(msg).__name__
            
            if msg_type == "HumanMessage":
                print(f"\n{i}. 👤 USUARIO:")
                print(f"   {msg.content[:200]}")
                
            elif msg_type == "AIMessage":
                print(f"\n{i}. 🤖 ASISTENTE:")
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    print(f"   📞 Llamando a herramientas:")
                    for tc in msg.tool_calls:
                        print(f"      • {tc['name']}")
                        print(f"        Args: {tc['args']}")
                else:
                    print(f"   {msg.content}")
                    
            elif msg_type == "ToolMessage":
                print(f"\n{i}. 🔧 RESULTADO DE HERRAMIENTA:")
                print(f"   {msg.content[:300]}")
        
        print("\n" + "="*70)
        print("RESPUESTA FINAL:")
        print("-" * 70)
        final_message = final_state["messages"][-1]
        print(final_message.content)
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\nERROR durante la ejecución: {e}")
        import traceback
        traceback.print_exc()

async def interactive_mode():
    """Modo interactivo: permite enviar múltiples mensajes."""
    print("\n" + "🎯" * 35)
    print("   ORQUESTADOR INTERACTIVO - Modo de Prueba")
    print("🎯" * 35)
    print("\nHerramientas disponibles:")
    print("  • email_classifier_tool - Procesa emails por ID")
    print("  • create_folder_tool - Crea carpetas")
    print("\nEjemplos de comandos:")
    print("  'Procesa el email con ID abc123'")
    print("  'Crea una carpeta llamada test-results'")
    print("  'Necesito una carpeta nueva llamada proyecto-2025'")
    print("\n⚠️  IMPORTANTE: Asegúrate de que los servidores MCP estén corriendo")
    print("   (ejecuta start_servers.ps1 en _local_testing)")
    print("\nEscribe 'salir' o 'exit' para terminar.")
    print("-" * 70)
    
    while True:
        try:
            user_input = input("\n💬 Tu mensaje: ").strip()
            
            if user_input.lower() in ['salir', 'exit', 'quit', 'q']:
                print("\n👋 ¡Hasta luego!")
                break
                
            if not user_input:
                print("⚠️  Por favor escribe un mensaje.")
                continue
            
            await test_orchestrator(user_input)
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrumpido por el usuario. ¡Hasta luego!")
            break
        except Exception as e:
            print(f"\n❌ Error inesperado: {e}")

async def main():
    """Punto de entrada principal."""
    import sys
    
    # Si se pasan argumentos, usar esos en lugar del modo interactivo
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        await test_orchestrator(message)
    else:
        await interactive_mode()

if __name__ == "__main__":
    asyncio.run(main())