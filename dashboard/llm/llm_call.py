import asyncio
import re

import httpx
from pyexpat import model

PROMPT = """
You are a finance expert.
Your task is to read a transaction description and assign one tag from the list below.
Return only the tag in [brackets]. No explanations. Only one tag per operation.

Categories:
Deuda: [Tarjetas de crédito, Préstamo caldera, Otros préstamos, Otros]
Educación: [Cursos, Clases de música, Otros]
Ocio: [Libros, Conciertos o espectáculos, Actividades al aire libre, Fotografía, Deporte, Cine o teatro, Otros]
Gastos diarios: [Comida, Restaurantes, Comida domicilio, Higiene personal, Ropa, Lavandería o tintorería, Peluquería o belleza, Suscripciones, Otros]
Regalos: [Regalos, Donativos (ONG), Otros]
Salud/médicos: [Médicos (dentista/oculista), Especialistas, Farmacia, Urgencias, Otros]
Vivienda: [Alquiler o hipoteca, Impuestos a la propiedad, Muebles, Artículos para el hogar, Mantenimiento, Mejoras, Mudanza, Otros]
Tecnología: [Dominios y alojamiento, Servicios online, Hardware, Software, Otros]
Transporte: [Combustible, Transporte público, Taxi/Uber, Otros]
Viajes: [Billetes de avión, Hoteles, Comida, Transporte, Ocio, Otros]
Servicios básicos: [Internet, Electricidad, Calefacción o gas, Otros]
Otros: [General]

Example Input:
operation: Recibo Greenpeace Espana Nº Recibo 4327382473498
→ [Donativos (ONG)]

operation: Recibo Comercializadora Regulada, Gas Power, Nº 123213213123
→ [Calefacción o gas]

Now classify:
operation: {variable}
"""

prompt2 = """categorize bank operation with a tag. bank operation: {variable}
tag: [Tarjetas de crédito, Préstamo caldera, Otros préstamos, Otros, Cursos, Clases de música, Otros, Libros, Conciertos o espectáculos, Actividades al aire libre, Fotografía, Deporte, Cine o teatro, Otros, Comida, Restaurantes, Comida domicilio, Higiene personal, Ropa, Lavandería o tintorería, Peluquería o belleza, Suscripciones, Otros, Regalos, Donativos (ONG), Otros, Médicos (dentista/oculista), Especialistas, Farmacia, Urgencias, Otros, Alquiler o hipoteca, Impuestos a la propiedad, Muebles, Artículos para el hogar, Mantenimiento, Mejoras, Mudanza, Otros,"""


async def query_llm(
    prompt_template: str, variable: str, model: str = "mistral:7b-instruct-v0.2-q3_K_M"
) -> str:
    formatted_prompt = prompt_template.format(variable=variable)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": formatted_prompt, "stream": False},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json().get("response", "")

        # # Remove any <think>...</think> or standalone <think> tags
        # cleaned_response = re.sub(
        #     r"<think>.*?</think>", "", raw_response, flags=re.IGNORECASE | re.DOTALL
        # )

        # return cleaned_response


if __name__ == "__main__":
    result = asyncio.run(
        query_llm(
            PROMPT,
            # "Recibo Greenpeace Espana Nº Recibo 4327382473498 Bbjmwds Ref. Mandato 3213213213, De",
            "Recibo Comercializadora Regulada, Gas Power, Gas Power32412343241234 Nº Recibo 123213213123 Bbjnhrk",
        )
    )
    print(result)
