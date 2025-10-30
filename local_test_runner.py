# local_test_runner.py

import json
import asyncio
from handler import lambda_handler

async def main():
    mock_api_gateway_event = {
        "body": json.dumps({
            "value": [
                {
                    "subscriptionId": "a-fake-subscription-guid",
                    "changeType": "created",
                    "resource": "Users/a-fake-user-guid/Messages('AAMkAGVmMDEzMTM4LTZmYWUtNDdkNC1hMDZiLTU1N2Y5MDRjYTE3MwBGAAAAAADoQ-6Y3-06RL1k_yb8_IKwBwD9P1jW-vN8Q53rNnoD52QCAAAAAAEMAAD9P1jW-vN8Q53rNnoD52QCAAAX_UCTAAA=')",
                    "clientState": "secretClientValue",
                    "tenantId": "a-fake-tenant-guid"
                }
            ]
        })
    }
    mock_context = None

    print("--- INICIANDO PRUEBA LOCAL DEL ORQUESTADOR LAMBDA ---")
    print("Simulando una invocación desde API Gateway...")

    response = await lambda_handler(mock_api_gateway_event, mock_context)

    print("\n--- PRUEBA FINALIZADA ---")
    print("Respuesta final de la Lambda:")
    
    print(f"Status Code: {response['statusCode']}")
    print("Cuerpo de la Respuesta:")
    print(json.dumps(json.loads(response["body"]), indent=2))

if __name__ == "__main__":
    asyncio.run(main())