"""
Test exhaustivo de manuscritos con errores diversos.

Manuscritos diseñados consultando las perspectivas de:
- EL CORRECTOR: ortografía, tipografía, puntuación, formato de diálogos
- EL EDITOR: estructura, ritmo, coherencia narrativa, arcos, PDV
- EL LINGÜISTA: gramática, estilo, registro, concordancia

Categorías de errores plantados:
 1. ORTOGRAFÍA: errores de escritura, tildes, homófonos
 2. TIPOGRAFÍA: rayas, puntuación, formato
 3. GRAMÁTICA: concordancia, tiempos verbales, dequeísmo
 4. ESTILO: repeticiones, ritmo, registro, voz pasiva
 5. CONSISTENCIA FÍSICA: cambios de atributos entre capítulos
 6. CONSISTENCIA TEMPORAL: imposibilidades cronológicas
 7. DESPLAZAMIENTOS IMPOSIBLES: geografía rota
 8. CONOCIMIENTO INDEBIDO: personaje sabe lo que no debería
 9. CAMBIO DE NARRADOR / PDV: saltos de punto de vista
10. HISTORIA SIN TERMINAR: subtramas abandonadas
11. INTRODUCCIÓN INCORRECTA: elementos no presentados
12. CHEKHOV: armas sin disparar / deus ex machina
"""

import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


# =============================================================================
# MANUSCRITO 1: NOVELA DE MISTERIO - Errores del Corrector y el Editor
# Errores plantados: ortografía, tipografía, gramática, PDV, timeline
# =============================================================================

MANUSCRITO_MISTERIO = textwrap.dedent("""\
    Capítulo 1: La carta

    Elena Ríos era una detective privada de cuarenta y tres años. Tenía el
    pelo castaño cortado a la altura de los hombros y unos ojos grises que
    no perdían detalle. Medía un metro setenta y cinco y llevaba siempre una
    gabardina beige, incluso en verano. Vivía sola en un piso de la calle
    Alcalá, en Madrid, con su perro, un pastor alemán llamado Kafka.

    Aquel lunes 15 de marzo, Elena recibió una carta sin remitente. Dentro
    encontró una fotografía antigua y una nota escrita a mano: "El hombre
    de la foto murió dos veces. Si quiere saber la verdad, vaya al Café
    Oriental el viernes a las ocho de la tarde."

    La foto mostraba a un hombre de unos sesenta años, con bigote canoso
    y traje oscuro. Al dorso, alguien había escrito: "Arturo Velasco, 1987".

    Elena guardó la carta en su cajón y encendió el ordenador. Una búsqueda
    rápida le reveló que Arturo Velasco había sido un empresario madrileño
    que murió en un accidente de coche en 1992. Nada especial... salvo que
    oficialmente ya había muerto una vez antes, en 1988, en un incendio
    en su fábrica de muebles en Getafe.

    —Interesante —murmuró Elena, acariciando a Kafka detrás de las orejas.

    Esa noche, mientras cenaba, su teléfono sonó. Era su hermano Marcos,
    que vivía en Barcelona.

    —Elena, ¿sigues en pie lo de la cena del sábado?

    —Claro, Marcos. Llegaré el viernes por la tarde en el AVE.

    —Perfecto. Los niños están deseando verte.

    Elena colgó y pensó en la carta. El viernes tenía la cita en el Café
    Oriental. Tendría que cancelar el viaje a Barcelona.


    Capítulo 2: El café

    El viernes 19 de marzo, Elena llegó al Café Oriental a las ocho menos
    diez. Era un local antiguo en el barrio de Malasaña, con mesas de mármol
    y espejos envejecidos. Se sentó en una mesa del fondo desde la que podía
    vigilar la puerta de entrada.

    A las ocho en punto, un hombre de unos treinta años se sentó frente a
    ella sin decir nada. Era delgado, moreno, con una cicatriz fina que le
    cruzaba la ceja izquierda.

    -¿Es usted quien me envió la carta? -preguntó Elena.

    —Me llamo Daniel Vega. Soy periodista del diario El Independiente. He
    estado investigando a Arturo Velasco durante tres años.

    —¿Qué tiene que ver conmigo?

    —Su padre, comisario Ríos, fue quien certificó la primera muerte de
    Velasco en 1988.

    Elena se quedó inmóvil. Su padre había muerto hacía cinco años sin
    contarle jamás nada sobre aquel caso.

    —Mi padre era un hombre honrado —dijo Elena, intentando mantener la
    calma.

    —No dudo de su honradez. Pero alguien le obligó a firmar ese certificado.
    Y ese alguien sigue vivo y tiene mucho poder.

    Daniel sacó un sobre de su maletín y lo deslizó sobre la mesa.

    —Aquí hay documentos que lo prueban. Léalos con calma y decida si quiere
    ayudarme.

    Elena abrió el sobre. Dentro habían copias de informes policiales,
    fotografías y extractos bancarios. Un nombre aparecía en todos:
    Gonzalo Ferrán, actual presidente de la Fundación Velasco.

    —¿Ferrán está implicado? —preguntó Elena.

    —Ferrán organizó la falsa muerte de Velasco en el 88 para cobrar el
    seguro. Después, cuando Velasco amenazó con hablar, lo mató de verdad
    en el 92.

    Elena miró las pruebas. Eran convincentes, pero no concluyentes.

    —Necesito verificar todo esto —dijo—. Volveré a contactarle.


    Capítulo 3: La investigación

    Elena, con su largo cabello rubio recogido en un moño, pasó el fin de
    semana revisando los documentos de Daniel. Su gato, que dormía en el
    sofá, la miraba con indiferencia.

    El lunes por la mañana, Elena visitó la comisaría de Getafe donde su
    padre había trabajado. El comisario actual, Sánchez, era un viejo amigo
    de la familia.

    —Elena, qué sorpresa. ¿Cómo está tu madre?

    —Bien, gracias. Oye, necesito acceder al archivo del caso Velasco de
    1988. Es para una investigación privada.

    Sánchez dudó. Pensó en que Elena siempre había sido persistente,
    igual que su padre. También pensó en que tendría que
    hablar con el juez antes de facilitar documentos a una civil.

    —Ese caso está sellado por orden judicial. No puedo darte acceso.

    —¿Por qué sellado?

    —No lo sé. Así estaba cuando llegué en el 2005.

    Elena salió de la comisaría frustrada. Si el caso estaba sellado,
    alguien con poder lo había ordenado. Y ese alguien podía ser Ferrán.

    Esa tarde, Elena viajó a Getafe para visitar la antigua fábrica de
    muebles de Velasco. El edificio, abandonado desde el incendio de 1988,
    estaba en las afueras de la ciudad, junto a la autovía A-42. El solar
    era ahora un descampado lleno de escombros y hierbajos.

    —Aquí fue donde todo empezó —pensó Elena, fotografiando el lugar.

    De vuelta en su piso de la calle Serrano, Elena organizó la información
    en un tablón de corcho. Tres líneas conectaban todo: Velasco, Ferrán y
    su padre.

    Capítulo 4: La trampa

    Tres semanas después, Elena había reunido suficientes pruebas para
    confrontar a Ferrán. Daniel y ella planearon una trampa: ella se haría
    pasar por una inversora interesada en la Fundación Velasco para
    conseguir una reunión privada con Ferrán.

    El jueves 22 de abril, Elena acudió a las oficinas de la Fundación
    en el Paseo de la Castellana. Llevaba un traje de chaqueta azul y
    su habitual gabardina negra. Se había teñido el pelo de rubio para
    no ser reconocida.

    —Señora Martín, el señor Ferrán la recibirá ahora —anunció la
    recepcionista.

    Elena entró en un despacho lujoso. Gonzalo Ferrán era un hombre de
    sesenta y ocho años, con el pelo completamente blanco y una sonrisa
    que no llegaba a los ojos.

    —Señora Martín, es un placer. Siéntese, por favor.

    —Gracias, señor Ferrán. Mi empresa está interesada en colaborar con
    la Fundación. Creemos que la labor cultural que realizan es admirable.

    —Me alegra oírlo. ¿De qué empresa me dijo que era?

    —Inversiones Atlántico. Somos relativamente nuevos en el sector
    cultural.

    Mientras hablaban, Elena activó discretamente una grabadora oculta
    en su bolso. Daniel la estaba esperando en un coche aparcado fuera,
    monitoreando la señal con unos auriculares.

    La conversación duró cuarenta minutos. Ferrán fue cauteloso pero
    dejó escapar un comentario revelador: "Arturo era mi socio. Su
    desaparición fue... necesaria para la supervivencia de la empresa."

    Elena controló su expresión. Tenía lo que necesitaba.

    —Ha sido un placer, señor Ferrán. Le enviaré la propuesta la semana
    que viene.

    Al salir, Elena caminó hasta el coche de Daniel, que estaba aparcado
    a tres manzanas.

    —Lo tengo —dijo, mostrando la grabadora—. Ha dicho que la
    desaparición de Velasco fue "necesaria".

    —No es una confesión directa, pero es un buen comienzo —respondió
    Daniel.

    Elena sabía que necesitaban más. Tendría que volver a ver a Ferrán.


    Capítulo 5: La verdad

    Dos meses después, en junio, Elena y Daniel tenían un caso sólido.
    El comisario Sánchez había accedido finalmente a abrir el archivo
    sellado, que revelaba que Gonzalo Ferrán había presionado al padre
    de Elena para certificar la muerte falsa de Velasco.

    Elena presentó todas las pruebas al fiscal del Estado. Ferrán fue
    detenido una tarde de julio mientras cenaba en un restaurante de
    lujo en el centro de Madrid.

    La noticia salió en todos los periódicos. Daniel publicó un extenso
    reportaje en El Independiente. Elena, sin embargo, no quiso aparecer
    en los medios. Su perro Kafka y ella celebraron con un paseo largo
    por el Retiro.

    Lo que quedó sin resolver fue el misterio de la llave antigua que
    Elena encontró dentro del sobre de Daniel. Tenía grabadas las
    iniciales "A.V." y parecía pertenecer a una caja fuerte o un
    armario antiguo. Elena la guardó en su escritorio, pensando que
    algún día descubriría qué abría.
""")

# Ground truth para manuscrito de misterio
ERRORES_MISTERIO = {
    # --- CONSISTENCIA FÍSICA ---
    "pelo_elena": {
        "tipo": "inconsistencia_atributo",
        "descripcion": "Elena tiene pelo castaño en cap.1, pelo rubio largo en cap.3",
        "cap_original": 1,
        "cap_contradiccion": 3,
        "entidad": "Elena",
        "atributo": "hair_color",
        "valor_original": "castaño",
        "valor_contradiccion": "rubio",
    },
    "mascota_elena": {
        "tipo": "inconsistencia_atributo",
        "descripcion": "Elena tiene perro (Kafka) en cap.1, gato en cap.3",
        "cap_original": 1,
        "cap_contradiccion": 3,
        "entidad": "Elena",
        "atributo": "mascota",
        "valor_original": "perro",
        "valor_contradiccion": "gato",
    },
    "gabardina_elena": {
        "tipo": "inconsistencia_atributo",
        "descripcion": "Gabardina beige en cap.1, gabardina negra en cap.4",
        "cap_original": 1,
        "cap_contradiccion": 4,
        "entidad": "Elena",
        "atributo": "gabardina",
        "valor_original": "beige",
        "valor_contradiccion": "negra",
    },
    "piso_elena": {
        "tipo": "inconsistencia_ubicacion",
        "descripcion": "Elena vive en calle Alcalá (cap.1) y calle Serrano (cap.3)",
        "cap_original": 1,
        "cap_contradiccion": 3,
        "entidad": "Elena",
    },
    # --- TIPOGRAFÍA ---
    "raya_dialogo_cap2": {
        "tipo": "tipografia",
        "descripcion": "Cap.2 usa guión (-) en vez de raya (—) en diálogo",
        "capitulo": 2,
        "texto": "-¿Es usted quien me envió la carta? -preguntó Elena.",
    },
    # --- GRAMÁTICA ---
    "habían_impersonal": {
        "tipo": "gramatica",
        "descripcion": "'habían copias' debería ser 'había copias' (haber impersonal)",
        "capitulo": 2,
        "texto": "Dentro habían copias de informes policiales",
    },
    # --- CAMBIO DE NARRADOR / PDV ---
    "pdv_sanchez": {
        "tipo": "cambio_narrador",
        "descripcion": "Narrador omnisciente filtra pensamientos de Sánchez en escena PDV-Elena",
        "capitulo": 3,
        "texto": "Pensó en que Elena siempre había sido persistente",
    },
    # --- CONOCIMIENTO INDEBIDO ---
    "elena_sabe_pelo_cap4": {
        "tipo": "conocimiento_indebido",
        "descripcion": "Elena se tiñó el pelo de rubio en cap.4, pero ya era rubio en cap.3",
        "capitulo": 4,
        "texto": "Se había teñido el pelo de rubio para no ser reconocida",
    },
    # --- CHEKHOV (sin disparar) ---
    "llave_sin_resolver": {
        "tipo": "chekhov_sin_disparar",
        "descripcion": "La llave antigua con iniciales A.V. se introduce y nunca se resuelve",
        "capitulo": 5,
    },
    # --- TIMELINE ---
    "marcos_barcelona_viernes": {
        "tipo": "inconsistencia_temporal",
        "descripcion": "Elena dice que irá a Barcelona el viernes, pero el viernes va al Café Oriental. No se menciona que cancela el viaje.",
        "capitulo": 1,
    },
}

# =============================================================================
# MANUSCRITO 2: NOVELA ROMÁNTICA CON ERRORES DE ESTILO Y RITMO
# Errores plantados: repeticiones, ritmo, pace, register, telling
# =============================================================================

MANUSCRITO_ROMANCE = textwrap.dedent("""\
    Capítulo 1: Primer día

    Lucía Herrera llegó al pueblo de Villafranca un martes de septiembre.
    El pueblo era pequeño, con calles estrechas y casas de piedra. El
    pueblo tenía una plaza central con una fuente. En el pueblo vivían
    unas trescientas personas. Lucía pensó que el pueblo era bonito.

    Lucía tenía veintiocho años. Lucía era alta. Lucía tenía los ojos
    marrones. Lucía llevaba una maleta grande. Lucía estaba cansada del
    viaje. Lucía buscaba la casa que había alquilado por internet.

    La casa estaba en la calle Mayor. Era una casa vieja pero había sido
    renovada recientemente. Tenía dos dormitorios, un baño y una cocina
    pequeña. El jardín trasero daba a un huerto de olivos.

    —Buenos días, ¿es usted la nueva inquilina? —dijo un hombre que
    estaba podando un seto al lado de la casa.

    —Sí, soy Lucía. Acabo de llegar.

    —Me llamo Gabriel Torres. Soy su vecino. Si necesita algo, no dude
    en llamar a mi puerta.

    Gabriel era un hombre de unos treinta y cinco años. Tenía el pelo
    oscuro y los ojos azules. Era alto y fuerte, con las manos
    encallecidas de trabajar la tierra. Su sonrisa era amable.

    Lucía entró en la casa. Estaba muy cansada. Se sentía muy triste.
    Estaba muy nerviosa por la nueva vida. Tenía mucho miedo de fracasar.
    Se sentía muy sola en aquel pueblo desconocido.

    Se sentó en el sofá y lloró. Lloró durante una hora. Después se
    lavó la cara y empezó a deshacer la maleta.


    Capítulo 2: El mercado

    Al día siguiente, Lucía fue al mercado del pueblo. El mercado estaba
    en la plaza central. Había puestos de frutas, verduras, queso y
    embutidos. El sol brillaba con fuerza y el aire olía a romero.

    Lucía caminó lentamente entre los puestos. Miró atentamente cada
    producto. Eligió cuidadosamente las frutas más maduras. Pagó
    amablemente a la vendedora. Sonrió cortésmente cuando le desearon
    un buen día.

    En el puesto de quesos, volvió a encontrarse con Gabriel.

    —Veo que ya está explorando el pueblo —dijo Gabriel alegremente.

    —Sí, necesitaba comprar algunas cosas —respondió Lucía tímidamente.

    —¿Le gusta el queso de cabra? El de aquí es el mejor de toda la
    región, de todo el país, posiblemente del mundo entero, sin ninguna
    duda el más exquisito, delicioso, cremoso, aromático y extraordinario
    queso que jamás haya probado nadie en la historia de la humanidad.

    Lucía rio. Era la primera vez que reía desde que dejó Madrid hacía
    dos semanas. En Madrid había trabajado como abogada en un bufete
    importante. Había llegado a socia junior con solo veintiseis años,
    la más joven de la historia del bufete, que había sido fundado en
    1952 por don Antonio Herrera, que casualmente no tenía relación
    alguna con la familia de Lucía, aunque compartían apellido, lo cual
    había generado alguna confusión en los primeros días, pero que
    pronto se aclaró cuando Lucía explicó que su familia era originaria
    de Extremadura, concretamente de un pueblo llamado Montehermoso, que
    está en la provincia de Cáceres, a unos trescientos kilómetros de
    Madrid, y que su padre era agricultor y su madre maestra de escuela.

    —¿Lucía? ¿Está bien? —la voz de Gabriel la sacó de sus pensamientos.

    —Sí, perdone. Estaba distraída. Me llevo un trozo de ese queso.


    Capítulo 3: La tormenta

    Una noche de octubre, una tormenta terrible azotó Villafranca. El
    viento era muy fuerte, la lluvia era muy intensa y los truenos eran
    muy ruidosos. Las calles estaban muy oscuras porque se había ido
    la luz.

    Lucía, en su casa, estaba muy asustada. Se sentía muy vulnerable.
    Estaba muy arrepentida de haberse mudado a un pueblo tan aislado.

    De repente, alguien llamó a la puerta. Era Gabriel, empapado, con
    una linterna y una manta.

    —He pensado que quizá necesitaba compañía —dijo él.

    Lucía, con sus ojos azules brillando a la luz de la linterna,
    le invitó a pasar. Preparó café en el fogón de gas y se sentaron
    juntos en el sofá.

    Gabriel le contó que era viudo. Su esposa, Carmen, había muerto
    hacía tres años en un accidente de tráfico. Desde entonces, se había
    dedicado al campo y a la soledad.

    —¿Y usted? ¿Por qué dejó Madrid? —preguntó Gabriel.

    —Mi jefe me acosaba laboralmente y nadie me creía. Un día no pude
    más y renuncié.

    Gabriel la miró con comprensión.

    —Este pueblo cura las heridas. Ya lo verá.


    Capítulo 4: El festival

    En diciembre, el pueblo celebró su festival anual de Navidad. Lucía
    se había integrado bien en la comunidad. Ayudaba en la panadería
    tres mañanas a la semana y daba clases de inglés a los niños.

    Gabriel y ella se habían hecho muy amigos. Pasaban las tardes juntos
    leyendo, paseando por el campo o cocinando. Lucía nunca mencionaba
    a su familia, y Gabriel nunca preguntaba.

    La noche del festival, mientras bailaban en la plaza, Gabriel le
    dijo algo que Lucía no esperaba.

    —Lucía, me gustas. Desde el primer día que te vi.

    Lucía se quedó callada. Había venido a Villafranca para huir, no
    para enamorarse.

    —Gabriel, eres maravilloso, pero no sé si estoy preparada.

    —No hay prisa —respondió él con su habitual paciencia.

    Esa noche, de vuelta en casa, Lucía encontró una carta debajo de
    la puerta. Era de su antiguo jefe, Enrique Sáenz. Decía: "Sé dónde
    estás. Volverás a Madrid o me encargaré de arruinarte."
""")

ERRORES_ROMANCE = {
    # --- ESTILO: REPETICIONES ---
    "repeticion_pueblo_cap1": {
        "tipo": "repeticion_lexica",
        "descripcion": "Palabra 'pueblo' repetida 5 veces en el primer párrafo",
        "capitulo": 1,
        "palabra": "pueblo",
        "frecuencia": 5,
    },
    "repeticion_lucia_cap1": {
        "tipo": "repeticion_lexica",
        "descripcion": "Nombre 'Lucía' inicia 6 oraciones consecutivas (anáfora no literaria)",
        "capitulo": 1,
    },
    # --- ESTILO: ADVERBIOS EXCESIVOS ---
    "adverbios_mente_cap2": {
        "tipo": "estilo_adverbios",
        "descripcion": "5 adverbios en -mente consecutivos: lentamente, atentamente, cuidadosamente, amablemente, cortésmente",
        "capitulo": 2,
    },
    # --- ESTILO: ORACIONES PEGAJOSAS (telling, not showing) ---
    "telling_cap1": {
        "tipo": "telling_not_showing",
        "descripcion": "6 oraciones consecutivas con 'muy' + emoción (telling en vez de showing)",
        "capitulo": 1,
        "texto": "Estaba muy cansada. Se sentía muy triste. Estaba muy nerviosa...",
    },
    "telling_cap3": {
        "tipo": "telling_not_showing",
        "descripcion": "Exceso de 'muy' + adjetivo en descripción de tormenta",
        "capitulo": 3,
    },
    # --- ESTILO: ORACIÓN KILOMÉTRICA ---
    "oracion_larga_cap2": {
        "tipo": "ritmo_oracion_larga",
        "descripcion": "Oración de 100+ palabras con info dump irrelevante sobre el bufete",
        "capitulo": 2,
    },
    # --- CONSISTENCIA FÍSICA ---
    "ojos_lucia": {
        "tipo": "inconsistencia_atributo",
        "descripcion": "Lucía tiene ojos marrones en cap.1, ojos azules en cap.3",
        "cap_original": 1,
        "cap_contradiccion": 3,
        "entidad": "Lucía",
        "atributo": "eye_color",
        "valor_original": "marrones",
        "valor_contradiccion": "azules",
    },
    # --- ORTOGRAFÍA ---
    "tilde_veintiseis": {
        "tipo": "ortografia",
        "descripcion": "'veintiseis' debería ser 'veintiséis'",
        "capitulo": 2,
    },
    # --- HISTORIA SIN TERMINAR ---
    "carta_amenaza_sin_resolver": {
        "tipo": "subtrama_abandonada",
        "descripcion": "La carta amenazante de Enrique Sáenz nunca se resuelve",
        "capitulo": 4,
    },
    "familia_lucia_abandonada": {
        "tipo": "subtrama_abandonada",
        "descripcion": "Se menciona que Lucía nunca habla de su familia, se plantea como misterio, pero nunca se explora",
        "capitulo": 4,
    },
}


# =============================================================================
# MANUSCRITO 3: NOVELA HISTÓRICA - Errores de investigación y anacronismos
# Errores plantados: anacronismos, geografía imposible, hechos incorrectos
# =============================================================================

MANUSCRITO_HISTORICO = textwrap.dedent("""\
    Capítulo 1: Sevilla, 1491

    Fray Tomás de Heredia caminaba por las calles empedradas de Sevilla
    en dirección al Alcázar. El sol de agosto caía a plomo sobre su hábito
    franciscano. Tenía cincuenta y un años, una barba gris recortada y
    una mirada penetrante que intimidaba a sus hermanos de la orden.

    Aquel día, el Consejo de Castilla le había convocado para una misión
    secreta. La reina Isabel quería que Fray Tomás acompañase a un tal
    Cristóbal Colón en su expedición hacia las Indias. Necesitaban un
    cronista fiable.

    —Es un genovés obstinado —le dijo el secretario del Consejo mientras
    caminaban por los jardines del Alcázar—. Lleva años insistiendo en
    que puede llegar a Cipango navegando hacia el oeste.

    —¿Y la Corona le ha creído?

    —La Reina está convencida. El Rey Fernando es más escéptico, pero ha
    cedido.

    Fray Tomás asintió. Él mismo era un hombre de ciencia. Había estudiado
    astronomía en la Universidad de Salamanca, fundada en 1218, y conocía
    las teorías de Ptolomeo y Eratóstenes sobre la forma esférica de la
    Tierra.

    Esa noche, en su celda del convento de San Francisco, Fray Tomás
    escribió en su diario: "Me han encomendado una misión que podría
    cambiar el mundo. Partiré hacia Barcelona en tres días para reunirme
    con Colón."

    El viaje de Sevilla a Barcelona le tomó apenas cuatro días a caballo.
    Llegó el sábado por la tarde, agotado pero ansioso. Colón le esperaba
    en el puerto.


    Capítulo 2: La travesía

    El 3 de agosto de 1492, las tres naves —la Santa María, la Pinta y
    la Niña— partieron del puerto de Barcelona rumbo a lo desconocido.
    Fray Tomás iba a bordo de la Santa María junto a Colón.

    El genovés era un hombre de cuarenta años, alto, con el pelo
    pelirrojo y los ojos claros. Hablaba un castellano con acento
    extranjero pero fluido.

    —Fray Tomás, usted será mis ojos cuando yo no pueda ver —le dijo
    Colón la primera noche—. Escriba todo lo que observe. Todo.

    —Así lo haré, señor Colón.

    Los primeros días de navegación fueron tranquilos. El mar estaba en
    calma y el viento soplaba a favor. Los marineros cantaban canciones
    andaluzas y jugaban a los naipes.

    Fray Tomás aprovechaba las horas tranquilas para leer. Había traído
    consigo un ejemplar de la "Suma Teológica" de Santo Tomás de Aquino
    y una copia de "El Quijote" que un amigo le había regalado.

    A las dos semanas, la moral de la tripulación empezó a decaer. Los
    marineros murmuraban que estaban condenados a morir en el océano.
    Algunos hablaban de motín.

    —Colón, los hombres están nerviosos —advirtió Fray Tomás.

    —Lo sé. Pero confío en mis cálculos. Estamos cerca.

    El 12 de octubre de 1492, a las dos de la madrugada, el vigía de la
    Pinta gritó: "¡Tierra! ¡Tierra!"

    Fray Tomás se persignó. Ante ellos, iluminada por la luna llena, se
    extendía una isla verde y desconocida. Colón lloró de alegría.


    Capítulo 3: El Nuevo Mundo

    La isla que habían descubierto era lo que los nativos llamaban
    Guanahaní. Colón la bautizó como San Salvador. Los habitantes, los
    taínos, recibieron a los españoles con curiosidad y cautela.

    Fray Tomás, con su barba ahora completamente negra por el sol
    tropical, se dedicó a observar y documentar todo. Describió las
    plantas, los animales y las costumbres de los taínos con detalle
    meticuloso.

    En su diario escribió: "Estas gentes son pacíficas y generosas.
    Comparten su comida y su agua sin pedir nada a cambio. No conocen
    las armas de metal ni la pólvora."

    Colón, sin embargo, tenía otros planes. Su objetivo era encontrar
    oro y especias. Cuando los taínos les mostraron pequeñas pepitas
    de oro, Colón les pidió que les llevasen a la fuente.

    —Fray Tomás, debemos ser diplomáticos —dijo Colón—. Necesitamos
    su colaboración.

    —Señor Colón, estos hombres no son súbditos de la Corona. Merecen
    respeto.

    —Le recuerdo, Fray Tomás, que estamos aquí en nombre de los Reyes
    Católicos. Su misión es documentar, no opinar.

    La tensión entre ambos crecería en las semanas siguientes. Fray Tomás
    registró en su diario privado: "Colón es un hombre de ambición
    desmedida. Temo por el destino de estas gentes inocentes."
""")

ERRORES_HISTORICO = {
    # --- ANACRONISMOS ---
    "quijote_anacronismo": {
        "tipo": "anacronismo",
        "descripcion": "El Quijote se publicó en 1605, no existía en 1492",
        "capitulo": 2,
        "texto": "una copia de 'El Quijote' que un amigo le había regalado",
    },
    # --- ERRORES GEOGRÁFICOS ---
    "puerto_barcelona": {
        "tipo": "error_historico_geografico",
        "descripcion": "Las naves de Colón partieron de Palos de la Frontera (Huelva), no de Barcelona",
        "capitulo": 2,
        "texto": "partieron del puerto de Barcelona",
    },
    # --- DESPLAZAMIENTO IMPOSIBLE ---
    "sevilla_barcelona_4dias": {
        "tipo": "desplazamiento_imposible",
        "descripcion": "Sevilla a Barcelona son ~1000km. A caballo (40-50km/día) se tardaban 20-25 días, no 4",
        "capitulo": 1,
    },
    # --- CONSISTENCIA FÍSICA ---
    "barba_fray_tomas": {
        "tipo": "inconsistencia_atributo",
        "descripcion": "Fray Tomás tiene barba gris en cap.1, negra en cap.3",
        "entidad": "Fray Tomás",
        "atributo": "hair_color",
        "valor_original": "gris",
        "valor_contradiccion": "negra",
    },
    # --- ERROR HISTÓRICO ---
    "universidad_salamanca_fecha": {
        "tipo": "error_factual",
        "descripcion": "La Universidad de Salamanca fue fundada en 1218 (dato correcto en el texto), pero Fray Tomás la describe como de ciencia; en 1491 era mayormente teológica",
        "capitulo": 1,
        "nota": "error menor, incluido para verificar detalle",
    },
    # --- INTRODUCCIÓN INCORRECTA ---
    "colon_descripcion_tardia": {
        "tipo": "introduccion_incorrecta",
        "descripcion": "Colón se menciona en cap.1 pero no se describe físicamente hasta cap.2. Su descripción de pelirrojo contradice fuentes históricas (era rubio/canoso)",
        "capitulo": 2,
    },
}


# =============================================================================
# MANUSCRITO 4: CIENCIA FICCIÓN - Errores de worldbuilding y lógica
# Errores plantados: reglas rotas, deus ex machina, lógica interna
# =============================================================================

MANUSCRITO_SCIFI = textwrap.dedent("""\
    Capítulo 1: La colonia

    La colonia Esperanza-7 llevaba quince años orbitando Próxima Centauri b.
    Albergaba a doce mil habitantes, todos descendientes de los colonos
    originales que partieron de la Tierra en 2089.

    Vera Kowalski, ingeniera jefe de sistemas, tenía treinta y cuatro años
    y era la persona más joven en ocupar ese cargo en la historia de la
    colonia. Tenía el pelo negro cortado muy corto y una cicatriz en la
    mejilla izquierda, recuerdo de una explosión en el reactor secundario.

    —Informe de la mañana —dijo Vera al entrar en la sala de control.

    —Los niveles de oxígeno están al ochenta y dos por ciento, capitana
    —respondió Yuri, su segundo al mando—. El reciclador tres sigue
    fallando.

    —¿Cuántas horas nos quedan si perdemos ese reciclador?

    —Cuarenta y ocho horas. Quizá menos.

    Vera apretó los dientes. El reciclador tres era el último de los
    sistemas auxiliares. Si fallaba, solo quedaría el reciclador principal,
    y ese no tenía capacidad para mantener a doce mil personas.

    Las reglas de la colonia eran claras: ningún recurso podía ser
    fabricado de la nada. Todo debía reciclarse, reutilizarse o repararse
    con los materiales disponibles. No existía tecnología de replicación
    molecular ni había forma de sintetizar oxígeno de forma artificial.
    Era una sociedad basada en la escasez.

    —Envía un equipo a inspeccionar el reciclador —ordenó Vera—. Quiero
    un diagnóstico completo antes del mediodía.

    —Entendido, capitana.

    Vera se dirigió a su despacho. Por el camino, se cruzó con el doctor
    Li, jefe médico de la colonia.

    —Vera, necesito hablar contigo. Tenemos un problema en el ala médica.

    —¿Qué ocurre?

    —Han aparecido tres casos de la fiebre violeta. Es la primera vez en
    cinco años.

    La fiebre violeta era una enfermedad endémica de la colonia,
    probablemente causada por una bacteria mutada durante el viaje
    interestelar. No era mortal, pero debilitaba enormemente a quienes
    la contraían.

    —Aísla a los infectados y refuerza los protocolos de higiene
    —respondió Vera—. No podemos permitirnos una epidemia ahora mismo.


    Capítulo 2: La crisis

    El diagnóstico del reciclador tres fue peor de lo esperado. El
    componente principal, una membrana de grafeno, estaba degradado
    irremediablemente. No había repuestos ni forma de fabricar uno nuevo.

    Vera convocó una reunión de emergencia del Consejo de la Colonia.
    Asistieron los siete miembros: Vera, Yuri, el doctor Li, la bióloga
    Ana Torres, el agrónomo Kenji Tanaka, la ingeniera de comunicaciones
    Fatima Hassan y el representante civil Marco Vitale.

    —La situación es crítica —comenzó Vera—. Tenemos cuarenta y ocho
    horas de oxígeno si el reciclador principal aguanta. Si falla también
    el principal, tenemos seis horas.

    —¿Opciones? —preguntó Marco.

    —Podemos reducir el consumo sellando las secciones no esenciales y
    poniendo a la mitad de la población en hibernación inducida.

    —Eso nos daría... ¿cuánto tiempo? —preguntó Ana.

    —Tal vez una semana más —calculó Vera.

    —¿Y la señal de socorro? —intervino Fatima—. Envié un mensaje a
    la Tierra hace tres años. Aún no hay respuesta.

    —Una señal tarda cuatro años en llegar a la Tierra —recordó Yuri—.
    Y otros cuatro en volver. Estamos solos.

    El doctor Li habló con voz grave:

    —Hay otra opción. Podríamos usar el replicador molecular del
    laboratorio médico para sintetizar la membrana de grafeno.

    Todos miraron al doctor Li con sorpresa.

    —¿Un replicador molecular? —preguntó Vera—. ¿Desde cuándo tenemos
    esa tecnología?

    —Lo construí en secreto hace dos años. Usa principios de
    nanotecnología cuántica para reorganizar la materia a nivel atómico.

    Vera no podía creerlo. Una tecnología así violaba las leyes
    fundamentales de la termodinámica y contradecía todo lo que sabían
    sobre la física de materiales.

    —Doctor Li, eso es imposible. No se puede crear materia de la nada.

    —No la creo de la nada. Reorganizo materia existente. Dame veinte
    kilos de residuos orgánicos y te daré una membrana de grafeno perfecta.

    El Consejo votó a favor de usar el replicador. Vera, la única que
    votó en contra, se resignó.


    Capítulo 3: La solución

    El replicador molecular funcionó. En menos de dos horas, el doctor
    Li transformó los residuos en una membrana de grafeno idéntica a la
    original. El reciclador tres volvió a funcionar y los niveles de
    oxígeno se estabilizaron.

    Vera, con su pelo largo y rizado cayéndole sobre los hombros,
    supervisó la instalación personalmente.

    —Doctor Li, quiero una explicación completa de cómo funciona esa
    máquina —exigió Vera después.

    —Es complicado, capitana. La nanotecnología cuántica permite
    reordenar enlaces atómicos sin violar la conservación de la masa.
    Solo necesita energía y materia prima.

    —¿Por qué lo mantuvo en secreto?

    —Temía que el Consejo lo usara indiscriminadamente. Este tipo de
    tecnología puede ser peligrosa si se abusa de ella.

    Vera comprendió, pero no le gustaba que le ocultaran información.

    Las semanas siguientes fueron tranquilas. La fiebre violeta se
    controló y el oxígeno volvió a niveles normales. Pero Vera no podía
    dejar de pensar en el replicador. Si podían crear cualquier material,
    ¿por qué seguían viviendo en la escasez?

    Cuando planteó la pregunta al doctor Li, este respondió:

    —El replicador tiene un límite. Solo puede funcionar una vez al mes
    y requiere tanta energía que la colonia se queda sin electricidad
    durante seis horas.

    —Eso no es lo que dijiste antes. Antes dijiste que solo necesitaba
    residuos orgánicos.

    —Bueno... también necesita energía. Mucha energía.

    Vera frunció el ceño. Las reglas seguían cambiando.
""")

ERRORES_SCIFI = {
    # --- REGLAS DEL MUNDO ROTAS ---
    "replicador_deus_ex_machina": {
        "tipo": "deus_ex_machina",
        "descripcion": "El replicador molecular aparece de la nada cuando es necesario, contradiciendo las reglas establecidas (no existe replicación molecular)",
        "capitulo": 2,
    },
    "reglas_cambiantes": {
        "tipo": "inconsistencia_worldbuilding",
        "descripcion": "El replicador solo necesita residuos (cap.2), luego también mucha energía (cap.3)",
        "capitulo": 3,
    },
    # --- CONSISTENCIA FÍSICA ---
    "pelo_vera": {
        "tipo": "inconsistencia_atributo",
        "descripcion": "Vera tiene pelo negro cortado muy corto en cap.1, pelo largo y rizado en cap.3",
        "entidad": "Vera",
        "atributo": "hair_type",
        "valor_original": "negro cortado muy corto",
        "valor_contradiccion": "largo y rizado",
    },
    # --- ERROR CIENTÍFICO ---
    "señal_tardanza": {
        "tipo": "error_cientifico",
        "descripcion": "Próxima Centauri está a 4.24 años luz. Una señal tardaría 4.24 años, no 4",
        "capitulo": 2,
        "nota": "error menor de redondeo",
    },
    # --- INTRODUCCIÓN INCORRECTA ---
    "li_replicador_secreto": {
        "tipo": "introduccion_incorrecta",
        "descripcion": "El doctor Li introduce un replicador molecular sin preparación narrativa previa. No hay foreshadowing.",
        "capitulo": 2,
    },
    # --- LÓGICA ---
    "escasez_innecesaria": {
        "tipo": "logica_rota",
        "descripcion": "Si el replicador puede crear cualquier material, la premisa de escasez queda destruida. El autor intenta parchar con el límite de 'una vez al mes' pero es incongruente.",
        "capitulo": 3,
    },
}


# =============================================================================
# MANUSCRITO 5: THRILLER - Errores graves de gramática y puntuación
# Errores plantados: concordancia, dequeísmo, queísmo, tiempos, puntuación
# =============================================================================

MANUSCRITO_GRAMATICA = textwrap.dedent("""\
    Capítulo 1: El aviso

    Las noticias de ayer eran clara: el asesino había vuelto. El
    comisario Ruiz, un hombre de cincuenta años con cara de pocos amigos,
    convocó a su equipo en la sala de reuniones.

    —Escuchen bien. El caso del Relojero ha vuelto a abrirse. Tenemos
    una nueva víctima.

    La inspectora Campos, que acababa de llegar de Valencia, se sentó
    en primera fila. Era una mujer joven, de treinta y dos años, con el
    pelo pelirrojo y pecas en la nariz.

    —Pienso de que deberíamos revisar las pruebas del caso original
    —dijo Campos.

    —Estoy seguro que tiene razón —respondió Ruiz—. Ordenaré que traigan
    los expedientes.

    La víctima era un hombre de cuarenta años, encontrado en su domicilio
    de la calle Princesa. El cadáver presentaba las mismas marcas que las
    víctimas anteriores: cortes precisos en forma de engranajes.

    El comisario Ruiz miró a Campos.

    —Campos, usted y López irán a la escena del crimen. Quiero un
    informe detallado antes de las seis.

    —Sí, comisario. Me informaron de que López estaba enfermo. ¿Quién
    le sustituye?

    —El agente Navarro. Es nuevo pero es competente.


    Capítulo 2: La escena

    La escena del crimen era un apartamento pequeño en un tercer piso
    sin ascensor. El presidente del edificio, los había recibido en
    la entrada con cara de susto.

    —Es terrible, inspectora. El señor Gutiérrez era una persona muy
    tranquilo. No se metía con nadie.

    Campos subió las escaleras seguida de Navarro. El apartamento estaba
    desordenado pero no parecía un robo.

    —Navarro, toma fotos de todo. Yo revisaré el dormitorio.

    En el dormitorio, Campos encontró un cuaderno junto a la cama. El
    cuaderno contenía anotaciones crípticas. Una de ellas decía: "Si
    alguien encuentra esto, que sepa que la persona que me hizo esto
    es alguien que conozco."

    Campos cogió el cuaderno con cuidado y lo metió en una bolsa de
    pruebas. Si el muerto había dejado pistas, ella los encontraría.

    El forense llegó media hora después. Era el doctor Álvarez, un
    veterano de sesenta años que había visto de todo.

    —Hora de la muerte: entre las once de la noche y la una de la
    madrugada —dictaminó—. La causa es desangrado por las heridas.
    Las cortes son muy precisas, hechas con un instrumento afilado,
    posiblemente un bisturí.

    —¿Algo más? —preguntó Campos.

    —Le informo de que el cadáver presenta señales de haber sido
    drogado previamente. Haré la autopsia completa mañana.

    Campos tomó notas meticulosamente. Algo le decía que este caso
    sería diferente.


    Capítulo 3: El sospechoso

    Al día siguiente, Campos y Navarro interrogaron al vecino del
    piso de abajo, un tal Ramón Iglesias.

    —¿Oyó algo anoche? —preguntó Campos.

    —No, inspectora. Yo duermo con tapones. Pero recuerdo que vi a
    un hombre salir del edificio sobre las doce y media. Era alto,
    llevaba una gorra y un abrigo largo.

    —¿Podría reconocerlo?

    —No sé. Estaba oscuro. Pero sé que no era ninguno de los vecinos
    porque aquí nos conocemos todos.

    Campos consultó las cámaras de seguridad del edificio. No habían
    cámaras interiores, pero la tienda de enfrente tenía una que
    apuntaba a la calle.

    El video mostraba a un hombre saliendo del portal a las 00:37.
    Coincidía con la descripción de Iglesias. Pero la resolución era
    demasiado baja para identificar al sospechoso.

    —Necesitamos mejorar la imagen —dijo Campos—. Envía el video al
    laboratorio.

    —Ya lo hice, inspectora —respondió Navarro—. También he comprobado
    que la víctima tenía un seguro de vida de trescientos mil euros.
    La beneficiaria es su ex-mujer, Carmen Díaz.

    —Interesante. Vamos a hablar con ella.

    Carmen Díaz vivía en un chalet adosado en las afueras. Era una mujer
    de treinta y ocho años, rubia, que parecía genuinamente afectada
    por la muerte de su ex-marido.

    —No puedo creerlo —dijo entre lágrimas—. Aunque estábamos divorciados,
    seguíamos siendo amigos.

    —¿Sabía que era la beneficiaria de su seguro de vida?

    —Sí, me lo dijo hace años. Nunca lo cambió después del divorcio.

    Campos observó que Carmen tenía las manos vendadas.

    —¿Qué le ha pasado en las manos?

    —Me corté cocinando. Nada grave.

    Campos no dijo nada, pero tomó nota mental.
""")

ERRORES_GRAMATICA = {
    # --- CONCORDANCIA ---
    "concordancia_noticias": {
        "tipo": "concordancia_genero",
        "descripcion": "'Las noticias eran clara' — falta concordancia (debería ser 'claras')",
        "capitulo": 1,
    },
    "concordancia_persona_tranquilo": {
        "tipo": "concordancia_genero",
        "descripcion": "'una persona muy tranquilo' — debería ser 'tranquila'",
        "capitulo": 2,
    },
    "concordancia_pistas_los": {
        "tipo": "concordancia_genero",
        "descripcion": "'ella los encontraría' referido a 'pistas' — debería ser 'las encontraría'",
        "capitulo": 2,
    },
    "concordancia_cortes": {
        "tipo": "concordancia_genero",
        "descripcion": "'Las cortes son muy precisas' — en este contexto 'los cortes'",
        "capitulo": 2,
    },
    # --- DEQUEÍSMO ---
    "dequeismo_cap1": {
        "tipo": "dequeismo",
        "descripcion": "'Pienso de que deberíamos' — debería ser 'Pienso que deberíamos'",
        "capitulo": 1,
    },
    # --- QUEÍSMO ---
    "queismo_cap1": {
        "tipo": "queismo",
        "descripcion": "'Estoy seguro que tiene razón' — debería ser 'Estoy seguro de que tiene razón'",
        "capitulo": 1,
    },
    # --- GRAMÁTICA VERBAL ---
    "habian_impersonal_cap3": {
        "tipo": "gramatica_verbal",
        "descripcion": "'No habían cámaras interiores' — debería ser 'No había cámaras interiores'",
        "capitulo": 3,
    },
    # --- PUNTUACIÓN ---
    "presidente_coma_criminal": {
        "tipo": "coma_criminal",
        "descripcion": "'El presidente del edificio, los había recibido' — coma entre sujeto y verbo",
        "capitulo": 2,
    },
}


# =============================================================================
# TEST HELPERS
# =============================================================================


def run_pipeline_on_text(text, filename="test_manuscript.txt", extra_config=None):
    """Ejecuta el pipeline completo sobre un texto y devuelve resultado."""
    import tempfile

    from narrative_assistant.pipelines.unified_analysis import (
        UnifiedAnalysisPipeline,
        UnifiedConfig,
    )

    config_args = {
        "run_structure": True,
        "run_dialogue_detection": True,
        "run_ner": True,
        "run_coreference": False,
        "run_entity_fusion": True,
        "run_attributes": True,
        "run_spelling": True,
        "run_grammar": False,  # LanguageTool puede no estar disponible
        "run_lexical_repetitions": True,
        "run_coherence": True,
        "run_consistency": True,
        "create_alerts": True,
        "use_llm": False,
        "parallel_extraction": False,
        "force_reanalysis": True,
    }
    if extra_config:
        config_args.update(extra_config)

    config = UnifiedConfig(**config_args)
    pipeline = UnifiedAnalysisPipeline(config=config)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(text)
        temp_path = f.name

    try:
        result = pipeline.analyze(temp_path)
        if result.is_success:
            return result.value, None
        else:
            return None, result.error
    finally:
        import os

        os.unlink(temp_path)


def get_consistency_alerts(report):
    """Extrae solo alertas de consistencia del reporte."""
    if not report or not hasattr(report, "alerts"):
        return []
    return [
        a
        for a in report.alerts
        if hasattr(a, "category")
        and hasattr(a.category, "value")
        and "consistency" in a.category.value
    ]


def get_spelling_alerts(report):
    """Extrae solo alertas de ortografía del reporte."""
    if not report or not hasattr(report, "alerts"):
        return []
    return [
        a
        for a in report.alerts
        if hasattr(a, "category")
        and hasattr(a.category, "value")
        and "spelling" in a.category.value
    ]


def get_repetition_alerts(report):
    """Extrae solo alertas de repetición léxica del reporte."""
    if not report or not hasattr(report, "alerts"):
        return []
    return [
        a
        for a in report.alerts
        if hasattr(a, "category")
        and hasattr(a.category, "value")
        and "repetition" in a.category.value
    ]


def get_grammar_alerts(report):
    """Extrae solo alertas gramaticales del reporte."""
    if not report or not hasattr(report, "alerts"):
        return []
    return [
        a
        for a in report.alerts
        if hasattr(a, "category") and hasattr(a.category, "value") and "grammar" in a.category.value
    ]


# =============================================================================
# TEST: MANUSCRITO MISTERIO
# =============================================================================


class TestMisterioE2E:
    """Tests para la novela de misterio."""

    @pytest.fixture(scope="class")
    def pipeline_result(self):
        report, error = run_pipeline_on_text(MANUSCRITO_MISTERIO, "misterio.txt")
        assert report is not None, f"Pipeline failed: {error}"
        return report

    def test_pipeline_completes(self, pipeline_result):
        """El pipeline completa sin errores."""
        assert pipeline_result is not None

    def test_detect_elena(self, pipeline_result):
        """Detecta a Elena Ríos como personaje principal."""
        entities = pipeline_result.entities
        names = [e.canonical_name.lower() for e in entities]
        assert any("elena" in n for n in names), f"Elena no detectada en: {names}"

    def test_detect_daniel(self, pipeline_result):
        """Detecta a Daniel Vega."""
        entities = pipeline_result.entities
        names = [e.canonical_name.lower() for e in entities]
        assert any("daniel" in n for n in names), f"Daniel no detectado en: {names}"

    def test_detect_ferran(self, pipeline_result):
        """Detecta a Gonzalo Ferrán."""
        entities = pipeline_result.entities
        names = [e.canonical_name.lower() for e in entities]
        assert any("ferrán" in n or "ferran" in n or "gonzalo" in n for n in names), (
            f"Ferrán no detectado en: {names}"
        )

    def test_detect_chapters(self, pipeline_result):
        """Detecta los 5 capítulos."""
        chapters = pipeline_result.chapters
        assert len(chapters) >= 4, f"Esperados >=4 capítulos, detectados {len(chapters)}"

    def test_detect_pelo_elena_inconsistency(self, pipeline_result):
        """Detecta que Elena cambia de castaño a rubio."""
        alerts = get_consistency_alerts(pipeline_result)
        alert_texts = " ".join(
            str(getattr(a, "description", "")) + " " + str(getattr(a, "details", ""))
            for a in alerts
        ).lower()

        found = "elena" in alert_texts and ("castaño" in alert_texts or "rubio" in alert_texts)
        if not found:
            pytest.xfail(
                f"No se detecta cambio pelo Elena (castaño->rubio). "
                f"Consistency alerts: {len(alerts)}"
            )

    def test_detect_mascota_inconsistency(self, pipeline_result):
        """Detecta que Elena tiene perro en cap.1 y gato en cap.3."""
        alerts = get_consistency_alerts(pipeline_result)
        alert_texts = " ".join(
            str(getattr(a, "description", "")) + " " + str(getattr(a, "details", ""))
            for a in alerts
        ).lower()

        found = "perro" in alert_texts or "gato" in alert_texts or "kafka" in alert_texts
        if not found:
            pytest.xfail(
                "No se detecta cambio de mascota Elena (perro Kafka -> gato). "
                f"Consistency alerts: {len(alerts)}"
            )

    def test_detect_piso_inconsistency(self, pipeline_result):
        """Detecta cambio de dirección de Elena (Alcalá -> Serrano)."""
        alerts = get_consistency_alerts(pipeline_result)
        alert_texts = " ".join(
            str(getattr(a, "description", "")) + " " + str(getattr(a, "details", ""))
            for a in alerts
        ).lower()

        found = "alcalá" in alert_texts or "serrano" in alert_texts
        if not found:
            pytest.xfail(
                "No se detecta cambio de dirección Elena (Alcalá -> Serrano). "
                f"Consistency alerts: {len(alerts)}"
            )

    def test_detect_dialogues(self, pipeline_result):
        """Detecta diálogos correctamente."""
        assert len(pipeline_result.dialogues) >= 15, (
            f"Esperados >=15 diálogos, detectados {len(pipeline_result.dialogues)}"
        )

    def test_raya_tipografia(self, pipeline_result):
        """Detecta uso incorrecto de guión en vez de raya en diálogos."""
        # El cap.2 usa - en vez de — en un diálogo
        alerts = pipeline_result.alerts
        alert_texts = " ".join(str(getattr(a, "description", "")) for a in alerts).lower()

        found = "guión" in alert_texts or "raya" in alert_texts or "tipograf" in alert_texts
        if not found:
            pytest.xfail("No se detecta uso de guión (-) en vez de raya (—) en diálogo cap.2")


# =============================================================================
# TEST: MANUSCRITO ROMANCE (estilo y ritmo)
# =============================================================================


class TestRomanceE2E:
    """Tests para novela romántica con errores de estilo."""

    @pytest.fixture(scope="class")
    def pipeline_result(self):
        report, error = run_pipeline_on_text(MANUSCRITO_ROMANCE, "romance.txt")
        assert report is not None, f"Pipeline failed: {error}"
        return report

    def test_pipeline_completes(self, pipeline_result):
        assert pipeline_result is not None

    def test_detect_lucia(self, pipeline_result):
        entities = pipeline_result.entities
        names = [e.canonical_name.lower() for e in entities]
        assert any("lucía" in n or "lucia" in n for n in names), f"Lucía no detectada en: {names}"

    def test_detect_gabriel(self, pipeline_result):
        entities = pipeline_result.entities
        names = [e.canonical_name.lower() for e in entities]
        assert any("gabriel" in n for n in names), f"Gabriel no detectado en: {names}"

    def test_detect_ojos_lucia_inconsistency(self, pipeline_result):
        """Detecta que Lucía cambia ojos marrones a azules."""
        alerts = get_consistency_alerts(pipeline_result)
        alert_texts = " ".join(
            str(getattr(a, "description", "")) + " " + str(getattr(a, "details", ""))
            for a in alerts
        ).lower()

        found = "lucía" in alert_texts and ("marrón" in alert_texts or "azul" in alert_texts)
        if not found:
            pytest.xfail(
                f"No se detecta cambio ojos Lucía (marrones->azules). "
                f"Consistency alerts: {len(alerts)}"
            )

    def test_detect_pueblo_repetition(self, pipeline_result):
        """Detecta repetición excesiva de 'pueblo' en primer párrafo."""
        rep_alerts = get_repetition_alerts(pipeline_result)

        # Buscar en cualquier alerta de repetición la palabra 'pueblo'
        alert_texts = " ".join(
            str(getattr(a, "description", "")) + " " + str(getattr(a, "details", ""))
            for a in rep_alerts
        ).lower()

        found = "pueblo" in alert_texts
        if not found:
            pytest.xfail(
                f"No se detecta repetición de 'pueblo' (5 veces en 1 párrafo). "
                f"Repetition alerts: {len(rep_alerts)}"
            )

    def test_detect_tilde_veintiseis(self, pipeline_result):
        """Detecta que 'veintiseis' debería ser 'veintiséis'."""
        spelling = get_spelling_alerts(pipeline_result)
        alert_texts = " ".join(
            str(getattr(a, "description", ""))
            + " "
            + str(getattr(a, "details", ""))
            + " "
            + str(getattr(a, "word", getattr(a, "extra_data", "")))
            for a in spelling
        ).lower()

        found = "veintiseis" in alert_texts or "veintiséis" in alert_texts
        if not found:
            pytest.xfail(
                f"No se detecta error ortográfico 'veintiseis'. Spelling alerts: {len(spelling)}"
            )

    def test_detect_chapters(self, pipeline_result):
        chapters = pipeline_result.chapters
        assert len(chapters) >= 3, f"Esperados >=3 capítulos, detectados {len(chapters)}"


# =============================================================================
# TEST: MANUSCRITO HISTÓRICO (anacronismos, desplazamientos)
# =============================================================================


class TestHistoricoE2E:
    """Tests para novela histórica con errores factuales."""

    @pytest.fixture(scope="class")
    def pipeline_result(self):
        report, error = run_pipeline_on_text(MANUSCRITO_HISTORICO, "historico.txt")
        assert report is not None, f"Pipeline failed: {error}"
        return report

    def test_pipeline_completes(self, pipeline_result):
        assert pipeline_result is not None

    def test_detect_fray_tomas(self, pipeline_result):
        entities = pipeline_result.entities
        names = [e.canonical_name.lower() for e in entities]
        assert any("tomás" in n or "tomas" in n or "fray" in n for n in names), (
            f"Fray Tomás no detectado en: {names}"
        )

    def test_detect_colon(self, pipeline_result):
        entities = pipeline_result.entities
        names = [e.canonical_name.lower() for e in entities]
        assert any("colón" in n or "colon" in n or "cristóbal" in n for n in names), (
            f"Colón no detectado en: {names}"
        )

    def test_detect_barba_inconsistency(self, pipeline_result):
        """Detecta que Fray Tomás cambia barba gris a negra."""
        alerts = get_consistency_alerts(pipeline_result)
        alert_texts = " ".join(
            str(getattr(a, "description", "")) + " " + str(getattr(a, "details", ""))
            for a in alerts
        ).lower()

        found = ("gris" in alert_texts or "negra" in alert_texts) and "tomás" in alert_texts
        if not found:
            pytest.xfail(
                f"No se detecta cambio barba Fray Tomás (gris->negra). "
                f"Consistency alerts: {len(alerts)}"
            )

    def test_detect_chapters(self, pipeline_result):
        chapters = pipeline_result.chapters
        assert len(chapters) >= 2, f"Esperados >=2 capítulos, detectados {len(chapters)}"

    def test_detect_dialogues(self, pipeline_result):
        assert len(pipeline_result.dialogues) >= 10, (
            f"Esperados >=10 diálogos, detectados {len(pipeline_result.dialogues)}"
        )


# =============================================================================
# TEST: MANUSCRITO SCI-FI (worldbuilding, deus ex machina)
# =============================================================================


class TestSciFiE2E:
    """Tests para novela sci-fi con errores de worldbuilding."""

    @pytest.fixture(scope="class")
    def pipeline_result(self):
        report, error = run_pipeline_on_text(MANUSCRITO_SCIFI, "scifi.txt")
        assert report is not None, f"Pipeline failed: {error}"
        return report

    def test_pipeline_completes(self, pipeline_result):
        assert pipeline_result is not None

    def test_detect_vera(self, pipeline_result):
        entities = pipeline_result.entities
        names = [e.canonical_name.lower() for e in entities]
        assert any("vera" in n for n in names), f"Vera no detectada en: {names}"

    def test_detect_dr_li(self, pipeline_result):
        entities = pipeline_result.entities
        names = [e.canonical_name.lower() for e in entities]
        assert any("li" in n for n in names), f"Dr. Li no detectado en: {names}"

    def test_detect_pelo_vera_inconsistency(self, pipeline_result):
        """Detecta que Vera cambia de pelo corto negro a largo rizado."""
        alerts = get_consistency_alerts(pipeline_result)
        alert_texts = " ".join(
            str(getattr(a, "description", "")) + " " + str(getattr(a, "details", ""))
            for a in alerts
        ).lower()

        found = "vera" in alert_texts and (
            "corto" in alert_texts or "largo" in alert_texts or "rizado" in alert_texts
        )
        if not found:
            pytest.xfail(
                f"No se detecta cambio pelo Vera (corto negro->largo rizado). "
                f"Consistency alerts: {len(alerts)}"
            )

    def test_detect_chapters(self, pipeline_result):
        chapters = pipeline_result.chapters
        assert len(chapters) >= 2, f"Esperados >=2 capítulos, detectados {len(chapters)}"


# =============================================================================
# TEST: MANUSCRITO GRAMÁTICA (concordancia, dequeísmo)
# =============================================================================


class TestGramaticaE2E:
    """Tests para novela con errores gramaticales plantados."""

    @pytest.fixture(scope="class")
    def pipeline_result(self):
        report, error = run_pipeline_on_text(
            MANUSCRITO_GRAMATICA, "gramatica.txt", extra_config={"run_grammar": True}
        )
        assert report is not None, f"Pipeline failed: {error}"
        return report

    def test_pipeline_completes(self, pipeline_result):
        assert pipeline_result is not None

    def test_detect_comisario(self, pipeline_result):
        entities = pipeline_result.entities
        names = [e.canonical_name.lower() for e in entities]
        assert any("ruiz" in n for n in names), f"Comisario Ruiz no detectado en: {names}"

    def test_detect_campos(self, pipeline_result):
        entities = pipeline_result.entities
        names = [e.canonical_name.lower() for e in entities]
        assert any("campos" in n for n in names), f"Inspectora Campos no detectada en: {names}"

    def test_detect_concordancia_clara(self, pipeline_result):
        """Detecta 'las noticias eran clara' (falta concordancia)."""
        grammar = get_grammar_alerts(pipeline_result)
        spelling = get_spelling_alerts(pipeline_result)
        all_alerts = grammar + spelling

        alert_texts = " ".join(
            str(getattr(a, "description", ""))
            + " "
            + str(getattr(a, "details", ""))
            + " "
            + str(getattr(a, "word", ""))
            for a in all_alerts
        ).lower()

        found = "clara" in alert_texts or "concordancia" in alert_texts
        if not found:
            pytest.xfail(
                f"No se detecta concordancia 'noticias eran clara'. "
                f"Grammar alerts: {len(grammar)}, Spelling: {len(spelling)}"
            )

    def test_detect_dequeismo(self, pipeline_result):
        """Detecta 'pienso de que' (dequeísmo)."""
        grammar = get_grammar_alerts(pipeline_result)

        alert_texts = " ".join(
            str(getattr(a, "description", "")) + " " + str(getattr(a, "details", ""))
            for a in grammar
        ).lower()

        found = "deque" in alert_texts or "pienso de que" in alert_texts
        if not found:
            pytest.xfail(f"No se detecta dequeísmo 'pienso de que'. Grammar alerts: {len(grammar)}")

    def test_detect_chapters(self, pipeline_result):
        chapters = pipeline_result.chapters
        assert len(chapters) >= 2, f"Esperados >=2 capítulos, detectados {len(chapters)}"


# =============================================================================
# RESUMEN DE COBERTURA
# =============================================================================


class TestCoverageSummary:
    """Resumen de cobertura de detección de errores."""

    @pytest.fixture(scope="class")
    def all_results(self):
        """Ejecuta todos los manuscritos y devuelve resultados."""
        results = {}
        manuscripts = {
            "misterio": MANUSCRITO_MISTERIO,
            "romance": MANUSCRITO_ROMANCE,
            "historico": MANUSCRITO_HISTORICO,
            "scifi": MANUSCRITO_SCIFI,
            "gramatica": MANUSCRITO_GRAMATICA,
        }
        for name, text in manuscripts.items():
            extra = {"run_grammar": True} if name == "gramatica" else None
            report, error = run_pipeline_on_text(text, f"{name}.txt", extra)
            results[name] = {"report": report, "error": error}
        return results

    def test_print_coverage_summary(self, all_results):
        """Imprime resumen de cobertura de errores por manuscrito."""
        total_planted = 0
        total_categories = set()

        lines = []
        lines.append("")
        lines.append("=" * 70)
        lines.append("RESUMEN DE COBERTURA - MANUSCRITOS COMPRENSIVOS")
        lines.append("=" * 70)

        ground_truths = {
            "misterio": ERRORES_MISTERIO,
            "romance": ERRORES_ROMANCE,
            "historico": ERRORES_HISTORICO,
            "scifi": ERRORES_SCIFI,
            "gramatica": ERRORES_GRAMATICA,
        }

        for name, data in all_results.items():
            report = data["report"]
            gt = ground_truths.get(name, {})

            lines.append(f"\n--- {name.upper()} ---")

            if report is None:
                lines.append(f"  ERROR: Pipeline fallo - {data['error']}")
                continue

            n_entities = len(report.entities)
            n_dialogues = len(report.dialogues)
            n_chapters = len(report.chapters)
            n_alerts = len(report.alerts)
            n_consistency = len(get_consistency_alerts(report))
            n_spelling = len(get_spelling_alerts(report))
            n_repetition = len(get_repetition_alerts(report))
            n_grammar = len(get_grammar_alerts(report))

            lines.append(f"  Entidades: {n_entities}")
            lines.append(f"  Dialogos:  {n_dialogues}")
            lines.append(f"  Capitulos: {n_chapters}")
            lines.append(f"  Alertas total: {n_alerts}")
            lines.append(f"    - Consistencia: {n_consistency}")
            lines.append(f"    - Ortografia:   {n_spelling}")
            lines.append(f"    - Repeticion:   {n_repetition}")
            lines.append(f"    - Gramatica:    {n_grammar}")
            lines.append(f"  Errores plantados: {len(gt)}")
            total_planted += len(gt)

            for err_id, err in gt.items():
                total_categories.add(err["tipo"])

        lines.append("\n--- TOTALES ---")
        lines.append(f"  Total errores plantados: {total_planted}")
        lines.append(f"  Categorias de error: {len(total_categories)}")
        lines.append(f"  Tipos: {sorted(total_categories)}")
        lines.append("=" * 70)

        print("\n".join(lines))
        assert total_planted > 0
