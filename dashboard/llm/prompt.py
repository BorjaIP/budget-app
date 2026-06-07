PROMPT = """You are a finance expert categorizing Spanish bank transactions.

Read the operation description and return EXACTLY ONE tag from the list below,
enclosed in square brackets, e.g. "[Comida]". Do not explain.

Categories (parent → subcategories):
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

Examples:
operation: Recibo Greenpeace Espana Nº Recibo 4327382473498
→ [Donativos (ONG)]

operation: Recibo Comercializadora Regulada, Gas Power, Nº 123213213123
→ [Calefacción o gas]

operation: Bizum Enviado a Marta Comida
→ [Comida]

Now classify:
operation: {variable}
"""
