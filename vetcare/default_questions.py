"""Encuesta orientativa, no instrumento científico. Todas las opciones son editables por versión."""

# Preguntas sin prejuicio por ingresos, tipo de vivienda o experiencia previa.
DEFAULTS = [
    (
        "Disponibilidad de tiempo",
        20,
        "Define una rutina diaria y un cuidador alternativo.",
        [
            (
                "¿Cuánto tiempo por semana puedes dedicar a alimentación, ejercicio y compañía?",
                [
                    ("Menos de 5 horas", 20),
                    ("Entre 5 y 10 horas", 50),
                    ("Entre 11 y 20 horas", 80),
                    ("Más de 20 horas", 100),
                ],
            ),
            (
                "Si trabajas o estudias varias horas, ¿qué apoyo tendrás?",
                [
                    ("Un cuidador responsable y disponible", 100),
                    ("Apoyo parcial y una rutina organizada", 75),
                    ("Necesito concretar un plan", 40),
                    ("No habrá nadie responsable", 0, "No hay responsable del cuidado"),
                ],
            ),
            (
                "¿Cómo organizarás las horas en que permanezca sola?",
                [
                    ("Con un plan adaptado a su especie y apoyo si hace falta", 100),
                    ("Revisaré sus necesidades antes de recibirla", 70),
                    ("No tengo un plan", 20),
                ],
            ),
            (
                "¿Puedes cumplir una rutina diaria de higiene, comida, ejercicio y compañía?",
                [
                    ("Sí, con tiempos y responsables definidos", 100),
                    ("Sí, con apoyo de otra persona", 100),
                    ("Aún debo organizarla", 40),
                ],
            ),
        ],
    ),
    (
        "Recursos para el cuidado",
        15,
        "Prepara un presupuesto de cuidado y una fuente de apoyo para imprevistos.",
        [
            (
                "¿Cómo cubrirás alimentación, vacunas y desparasitación?",
                [
                    ("Presupuesto propio o apoyo familiar confirmado", 100),
                    ("Cubro lo básico y completaré el plan preventivo", 65),
                    ("No he previsto recursos", 15),
                ],
            ),
            (
                "¿Qué harás frente a un gasto veterinario imprevisto?",
                [
                    ("Fondo, seguro o apoyo confirmado", 100),
                    ("Plan de ahorro o red de apoyo por concretar", 60),
                    ("No tengo un plan", 15),
                ],
            ),
            (
                "¿El presupuesto indicado considera las necesidades de esta mascota?",
                [
                    ("Sí, revisé alimentación y cuidados de su especie", 100),
                    ("Solicitaré orientación antes de la entrega", 80),
                    ("No lo he revisado", 25),
                ],
            ),
        ],
    ),
    (
        "Condiciones de vivienda",
        15,
        "Asegura permiso de tenencia, espacios protegidos y descanso seguro.",
        [
            (
                "¿Está permitida la tenencia de esta mascota en la vivienda?",
                [
                    ("Sí, tengo permiso o confirmación", 100),
                    ("Estoy gestionándolo antes de la entrega", 50),
                    ("No está permitida", 0, "Tenencia no permitida en la vivienda"),
                ],
            ),
            (
                "Sea casa, apartamento o vivienda arrendada, ¿cómo evitarás escapes y accidentes?",
                [
                    ("Espacios seguros, barreras y supervisión según la especie", 100),
                    ("Haré adaptaciones antes de la entrega", 75),
                    (
                        "Estará expuesta a riesgos sin protección",
                        0,
                        "Condiciones de vivienda peligrosas",
                    ),
                ],
            ),
            (
                "¿Dónde dormirá y cómo estará protegida del clima?",
                [
                    ("Lugar protegido, limpio y adecuado", 100),
                    ("Prepararé ese espacio antes de la entrega", 75),
                    (
                        "A la intemperie sin protección",
                        0,
                        "Sin protección frente al clima",
                    ),
                ],
            ),
        ],
    ),
    (
        "Atención veterinaria",
        15,
        "Acordemos un plan de prevención y atención médica.",
        [
            (
                "¿Cumplirás el esquema de vacunación y prevención indicado?",
                [
                    ("Sí, con seguimiento veterinario", 100),
                    ("Necesito orientación para organizarlo", 75),
                    (
                        "No proporcionaré esos cuidados",
                        0,
                        "Rechazo de cuidados veterinarios",
                    ),
                ],
            ),
            (
                "Si enferma o requiere tratamiento, ¿qué harás?",
                [
                    ("Buscar atención y cumplir el tratamiento indicado", 100),
                    ("Buscar ayuda y recursos para atenderla", 90),
                    (
                        "No la llevaré al veterinario",
                        0,
                        "Rechazo de atención veterinaria",
                    ),
                ],
            ),
            (
                "¿Conoces una clínica o forma de obtener atención?",
                [
                    ("Sí, tengo un contacto o red de apoyo", 100),
                    ("Lo definiré antes de recibirla", 75),
                    ("No tengo plan", 25),
                ],
            ),
        ],
    ),
    (
        "Aceptación familiar",
        10,
        "Confirma el acuerdo del hogar y planifica una adaptación gradual.",
        [
            (
                "¿Las personas del hogar conocen y aceptan la adopción?",
                [
                    ("Sí, o vivo solo y asumiré el cuidado", 100),
                    ("Falta confirmar con alguien", 50),
                    ("Existe oposición sin resolver", 10),
                ],
            ),
            (
                "Si hay otros animales, ¿cómo realizarás la adaptación?",
                [
                    ("Adaptación gradual y supervisada, o no hay otros animales", 100),
                    ("Pediré orientación antes de presentarlos", 85),
                    ("Los juntaré sin supervisión ni plan", 20),
                ],
            ),
        ],
    ),
    (
        "Conocimientos y aprendizaje",
        10,
        "Consulta alimentación por especie, adaptación y señales de alarma.",
        [
            (
                "¿Cómo te prepararás para alimentar y cuidar a esta especie?",
                [
                    ("Tengo experiencia y revisaré sus necesidades específicas", 100),
                    ("Soy principiante y buscaré orientación fiable", 100),
                    ("No quiero recibir orientación", 10),
                ],
            ),
            (
                "Ante señales de enfermedad o comportamiento inusual, ¿cómo actuarás?",
                [
                    ("Observar, proteger y consultar a un profesional", 100),
                    ("Pediré ayuda para reconocer las señales", 80),
                    ("Ignoraré los cambios", 0),
                ],
            ),
        ],
    ),
    (
        "Planes ante emergencias",
        10,
        "Confirma quién puede cuidar de la mascota ante viajes o cambios de vivienda.",
        [
            (
                "¿Quién la cuidará durante viajes o una emergencia personal?",
                [
                    ("Cuidador o servicio responsable confirmado", 100),
                    ("Una red de apoyo pendiente de confirmar", 60),
                    ("No tengo alternativa", 15),
                ],
            ),
            (
                "Si cambias de vivienda, ¿qué plan tienes?",
                [
                    ("Buscar un lugar compatible y mantener su cuidado", 100),
                    ("Pedir apoyo temporal y coordinar con la organización", 85),
                    ("Dejarla sin responsable", 0, "Riesgo de abandono"),
                ],
            ),
        ],
    ),
    (
        "Compromiso a largo plazo",
        5,
        "La adopción implica cuidado durante toda su vida y apoyo si las circunstancias cambian.",
        [
            (
                "¿Qué significa para ti el compromiso de adoptar?",
                [
                    ("Cuidado, compañía y atención durante toda su vida", 100),
                    ("Quiero conocer mejor sus necesidades antes de decidir", 65),
                    ("Solo la cuidaré por un tiempo", 10),
                ],
            ),
            (
                "Si no pudieras seguir cuidándola, ¿qué harías?",
                [
                    ("Contactar a VetCare y buscar una solución responsable", 100),
                    ("Buscar apoyo con seguimiento y sin abandonarla", 100),
                    (
                        "Abandonarla o entregarla sin comprobar su bienestar",
                        0,
                        "Riesgo de abandono",
                    ),
                ],
            ),
        ],
    ),
]
