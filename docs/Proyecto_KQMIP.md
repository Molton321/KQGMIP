

**Algoritmo Geométrico K\_QGMIP**

Análisis y Diseño de Algoritmos

*Proyecto 2026-1*

[1\.	Introducción	1](#introducción)

[1.1 Contexto del Proyecto	1](#1.1-contexto-del-proyecto)

[2\.	Fundamentos Teóricos de k-Particiones	1](#fundamentos-teóricos-de-k-particiones)

[2.1 Definición Formal de k-Particiones	1](#2.1-definición-formal-de-k-particiones)

[2.2 Complejidad del Espacio de k-Particiones	1](#2.2-complejidad-del-espacio-de-k-particiones)

[2.3 Interpretación Geométrica de k-Particiones	1](#2.3-interpretación-geométrica-de-k-particiones)

[3\.	Planteamiento del Problema	1](#planteamiento-del-problema)

[3.1 Formulación Matemática del Problema	1](#3.1-formulación-matemática-del-problema)

[3.2 Restricciones y Consideraciones	1](#3.2-restricciones-y-consideraciones)

[3.3 Alcance del Proyecto	1](#3.3-alcance-del-proyecto)

[4\.	Entregables del Proyecto	1](#entregables-del-proyecto)

[4.1 Componentes de Software	1](#4.1-componentes-de-software)

[4.2 Documentación Técnica	1](#4.2-documentación-técnica)

[4.3 Resultados Experimentales	1](#4.3-resultados-experimentales)

[4.4 Presentación Final	1](#4.4-presentación-final)

[4.5 Criterios de Evaluación	1](#4.5-criterios-de-evaluación)

[5\.	Observaciones Finales	1](#observaciones-finales)

1. # **Introducción** {#introducción}

En trabajos anteriores se ha desarrollado con la implementación de algoritmos eficientes para resolver el problema de la Partición de Mínima Información (MIP) en el contexto de la Teoría de la Información Integrada (IIT). Específicamente, se trabajó con el algoritmo QNodes, basado en la minimización de funciones submodulares mediante el algoritmo de Queyranne, y posteriormente se desarrolló la estrategia geométrica GeoMIP, que reformula el problema aprovechando la correspondencia natural entre estados binarios del sistema y vértices de un hipercubo n-dimensional.

Ambas estrategias han demostrado reducciones significativas en la complejidad computacional respecto a los métodos exhaustivos tradicionales, permitiendo el análisis de sistemas con hasta 20-23 nodos en tiempos razonables. Sin embargo, estas implementaciones se han centrado exclusivamente en el caso de bi-particiones, donde el sistema se divide en exactamente dos partes independientes. Esta restricción, si bien conceptualmente clara y algorítmicamente tratable, no explora completamente el espacio de posibles divisiones del sistema.

El presente proyecto propone extender tanto las estrategias geométrica GeoMIP como QNodes al caso general de k-particiones, donde el sistema puede dividirse en k partes independientes con k ≥ 2\. Esta extensión no solo representa un desafío algorítmico interesante, sino que también tiene implicaciones teóricas profundas para la comprensión de la estructura causal de sistemas complejos y para la cuantificación de la información integrada en configuraciones más generales.

## **1.1 Contexto del Proyecto** {#1.1-contexto-del-proyecto}

La Teoría de la Información Integrada (IIT) proporciona un marco matemático riguroso para cuantificar la conciencia en sistemas físicos. Un componente fundamental de esta teoría es el concepto de Partición de Mínima Información (MIP), que identifica cómo debe dividirse un sistema para minimizar la pérdida de información integrada. Esta división revela la estructura causal del sistema y cuantifica su irreducibilidad, propiedades que según IIT distinguen el procesamiento consciente del inconsciente.

En el caso de bi-particiones, el problema consiste en encontrar una división del sistema V en dos partes S₁ y S₂ tal que se minimice la discrepancia entre la dinámica del sistema original y la dinámica reconstruida a partir de las partes. Esta discrepancia se cuantifica mediante la Earth Mover's Distance (EMD) con métrica de Hamming, que mide el trabajo mínimo necesario para transformar una distribución de probabilidad en otra.

Se han implementado dos estrategias principales para resolver este problema. La estrategia QNodes, basada en la demostración de que la función de pérdida EMD es submodular para sistemas Markovianos discretos, logra reducir la complejidad de O(2ⁿ) a O(N³) mediante el algoritmo de Queyranne. Por su parte, la estrategia geométrica GeoMIP reformula el problema aprovechando la representación del espacio de estados como un hipercubo n-dimensional, calculando una tabla de costos de transiciones entre estados que permite identificar biparticiones óptimas sin evaluación exhaustiva del espacio de soluciones.

2. # **Fundamentos Teóricos de k-Particiones** {#fundamentos-teóricos-de-k-particiones}

El concepto de k-partición generaliza la idea de bi-partición al caso donde el sistema puede dividirse en k partes independientes en lugar de solo dos. Esta generalización, aparentemente simple en su formulación, introduce complejidades tanto teóricas como computacionales que requieren análisis cuidadoso.

## **2.1 Definición Formal de k-Particiones** {#2.1-definición-formal-de-k-particiones}

Consideremos un sistema V compuesto por n variables binarias. Una k-partición del sistema es una división de V en k subconjuntos disjuntos S₁, S₂, ..., Sₖ tales que la unión de todos los subconjuntos recupera el sistema completo y ningún par de subconjuntos comparte elementos. Formalmente, una k-partición satisface las siguientes condiciones: la unión de todos los subconjuntos S₁ ∪ S₂ ∪ ... ∪ Sₖ es igual a V, la intersección de cualquier par de subconjuntos Sᵢ ∩ Sⱼ es el conjunto vacío para todo i ≠ j, y cada subconjunto Sᵢ es no vacío.

La evaluación de una k-partición requiere comparar la dinámica del sistema original con la dinámica reconstruida a partir de las k partes independientes. Bajo el principio de independencia condicional, la distribución de probabilidad conjunta del sistema particionado se puede expresar como el producto tensorial de las distribuciones marginales de cada parte. La discrepancia entre el sistema original y el sistema reconstruido se cuantifica mediante la misma métrica EMD utilizada en el caso de bi-particiones, pero ahora aplicada a la reconstrucción k-partita.

## **2.2 Complejidad del Espacio de k-Particiones** {#2.2-complejidad-del-espacio-de-k-particiones}

El número de posibles k-particiones de un conjunto de n elementos está dado por los números de Stirling del segundo tipo, denotados S(n,k). Estos números crecen extremadamente rápido con n y k, representando un desafío computacional significativo. Por ejemplo, para un sistema de solo 10 variables, el número de posibles tri-particiones (k=3) es de 9,330 configuraciones, mientras que para 15 variables este número alcanza más de 2.3 millones de tri-particiones posibles.

Esta explosión combinatoria hace inviable la búsqueda exhaustiva para sistemas de tamaño moderado a grande. Sin embargo, es importante notar que no todas las k-particiones son igualmente significativas desde el punto de vista de la estructura causal del sistema. Muchas particiones pueden ser triviales o redundantes, lo que sugiere que enfoques inteligentes de búsqueda podrían identificar particiones óptimas o cuasi-óptimas sin necesidad de evaluación exhaustiva.

Además, la relación entre bi-particiones y k-particiones es importante. Toda bi-partición es una 2-partición, y conceptualmente, una k-partición puede verse como el resultado de aplicar k-1 bi-particiones sucesivas al sistema. Esta observación sugiere que las técnicas desarrolladas para bi-particiones podrían extenderse o adaptarse al caso k-partito, aunque la optimalidad de este enfoque greedy no está garantizada.

## **2.3 Interpretación Geométrica de k-Particiones** {#2.3-interpretación-geométrica-de-k-particiones}

La estrategia geométrica GeoMIP se fundamenta en la representación del espacio de estados como un hipercubo n-dimensional, donde cada vértice corresponde a un posible estado binario del sistema y las aristas conectan estados que difieren en exactamente una variable. En este marco geométrico, una bi-partición puede interpretarse como la división del hipercubo mediante un hiperplano, separando el espacio en dos regiones correspondientes a las dos partes de la partición.

Esta interpretación geométrica se extiende naturalmente al caso de k-particiones. Una k-partición del sistema corresponde a la división del hipercubo n-dimensional mediante k-1 hiperplanos, creando k regiones disjuntas que particionan completamente el espacio de estados. La configuración geométrica de estos hiperplanos determina qué variables se asignan a cada parte de la partición y, por lo tanto, afecta directamente la pérdida de información asociada a la partición.

Un aspecto crucial de la estrategia GeoMIP es la tabla de costos de transiciones entre estados, que cuantifica la energía o inercia requerida para la transición entre cada par de estados del sistema. Esta tabla, calculada mediante una función de costo que incorpora la distancia de Hamming entre estados y la estructura topológica del hipercubo, captura información sobre la estructura causal del sistema que es independiente de la forma específica de particionarlo. Por lo tanto, la misma tabla de costos calculada para el análisis de bi-particiones puede potencialmente reutilizarse para el análisis de k-particiones, evitando la necesidad de recalcular esta información costosa.

3. # **Planteamiento del Problema** {#planteamiento-del-problema}

El objetivo central de este proyecto es diseñar e implementar una extensión de la estrategia geométrica GeoMIP que permita identificar la k-Partición de Mínima Información (k-MIP) para valores de k (3≤k≤5). Esta extensión debe aprovechar la infraestructura existente, incluyendo la representación del espacio de estados como hipercubo n-dimensional, la tabla de costos de transiciones entre estados, y las estructuras de datos N-Cubos ya implementadas. Igualmente, se debe diseñar un extension para la estrategia QNodes, que busque identificar la k-Partición de Mínima Información (QN-MIP) para valores de k (3≤k≤5).

## **3.1 Formulación Matemática del Problema** {#3.1-formulación-matemática-del-problema}

Dado un sistema V con n variables binarias y su correspondiente Matriz de Probabilidad de Transición que especifica la dinámica P(Vₜ₊₁|Vₜ), el problema consiste en encontrar una k-partición óptima del sistema que minimice la discrepancia entre la distribución de probabilidad del sistema original y la distribución reconstruida a partir de las k partes independientes.

Formalmente, se busca encontrar la k-partición de V en subconjuntos S₁, S₂, ..., Sₖ que minimice la función de pérdida δₖ definida como la Earth Mover's Distance entre la distribución original del sistema y el producto tensorial de las distribuciones marginales de cada parte. El problema requiere no solo encontrar una partición con pérdida baja, sino identificar la partición óptima global entre todas las posibles k-particiones del sistema.

Es importante destacar que el problema debe resolverse para diferentes valores de k, típicamente k ∈ {2, 3, 4, 5}, permitiendo analizar cómo la estructura óptima de partición del sistema varía con el número de partes permitidas. Esta información puede revelar aspectos fundamentales sobre la organización modular del sistema y la naturaleza de sus dependencias causales.

## **3.2 Restricciones y Consideraciones** {#3.2-restricciones-y-consideraciones}

La implementación debe mantener compatibilidad con la arquitectura existente del proyecto, heredando de la clase base SIA y siguiendo los patrones de diseño establecidos en semestres anteriores. Esto asegura la interoperabilidad con las herramientas de validación y comparación ya desarrolladas, particularmente la posibilidad de comparar resultados con las implementaciones de referencia PyPhi y QNodes para casos donde estas sean computacionalmente viables.

La solución debe ser capaz de procesar los mismos conjuntos de datos de prueba utilizados en proyectos anteriores, permitiendo validación cruzada y análisis comparativo de rendimiento. Los datasets incluyen sistemas con diferentes números de variables, desde casos pequeños de validación con 3-6 nodos hasta sistemas de escala moderada con 10-15 nodos, y casos de escalabilidad con 20 o más nodos donde solo aproximaciones heurísticas podrían ser viables.

Un aspecto fundamental es que la implementación debe reutilizar eficientemente los componentes existentes. Particularmente, la tabla de costos de transiciones entre estados, que constituye uno de los cálculos más costosos del método geométrico, debe calcularse una única vez y luego utilizarse para evaluar todas las k-particiones candidatas independientemente del valor de k. Esta reutilización es crucial para mantener la eficiencia computacional del enfoque, así como todas las consideraciones  formales de ambas estrategias pero abiertas a modificar aquellas características (estructuras de datos o procedimientos) que no alteren la fundamentacion teórica conceptual  de ambas estrategias.

## **3.3 Alcance del Proyecto** {#3.3-alcance-del-proyecto}

El proyecto debe producir una implementación funcional que extienda a GeoMIP y a QNodes para identificar k-particiones óptimas con k comprendido entre 2 y 5\. Para valores pequeños de k y sistemas de tamaño reducido, donde la búsqueda exhaustiva es computacionalmente viable, la implementación debe ser capaz de encontrar la k-MIP óptima global con certeza. Para sistemas más grandes o valores mayores de k, donde la búsqueda exhaustiva se vuelve intratable, se espera que la implementación encuentre k-particiones de alta calidad, aunque no necesariamente óptimas globales, en tiempos razonables.

La evaluación del proyecto considerará tanto la calidad de las soluciones encontradas como la eficiencia computacional del enfoque. Se espera que para sistemas de tamaño moderado, la implementación logre speedups significativos respecto a métodos de búsqueda exhaustiva, manteniendo al mismo tiempo alta precisión en la identificación de particiones óptimas o cuasi-óptimas. El análisis debe incluir comparación con las bi-particiones encontradas por GeoMIP  y QNodes original para k=2 , validando que la extensión reproduce correctamente los resultados previos en este caso base.

Además de los aspectos algorítmicos, el proyecto debe incluir análisis experimental comprehensivo que caracterice el comportamiento del método propuesto. Esto incluye estudiar cómo la calidad de las soluciones y los tiempos de ejecución escalan con el tamaño del sistema n y el número de particiones k, identificar patrones en las k-particiones óptimas encontradas que revelen estructura modular en los sistemas analizados, y comparar diferentes estrategias o variantes del enfoque si se implementan múltiples alternativas.

4. # **Entregables del Proyecto** {#entregables-del-proyecto}

El proyecto requiere la entrega de componentes de software, documentación técnica y análisis experimental que demuestren la comprensión del problema, la calidad de la solución implementada y la capacidad de análisis crítico de los resultados obtenidos.

## **4.1 Componentes de Software** {#4.1-componentes-de-software}

Se debe entregar una implementación completa y funcional que extienda las estrategias para k-particiones. El código debe organizarse con las nuevas clases que hereden de la clase base SIA, siguiendo la estructura modular establecida en el proyecto. La implementación debe ubicarse en el archivo correspondiente dentro de la jerarquía de directorios del proyecto, específicamente en src/controllers/strategies/, manteniendo consistencia con las estrategias existentes.

El código debe incluir como mínimo la implementación de los métodos principales que encuentra la k-MIP para un valor de k dado, métodos auxiliares necesarios para la evaluación de k-particiones candidatas utilizando la tabla de costos existente, funciones para el cálculo de distribuciones marginales y productos tensoriales de k términos, y mecanismos para identificar y generar k-particiones candidatas para evaluación. La implementación debe reutilizar eficientemente los componentes existentes de GeoMIP, particularmente la infraestructura de N-Cubos y el cálculo de la tabla de costos de transiciones, asi como de QNodes.

El código entregado debe estar completamente documentado mediante docstrings que expliquen la función de cada método, los parámetros de entrada y salida, y las asunciones o precondiciones importantes. Se deben incluir comentarios en línea para secciones de código particularmente complejas o no obvias. Además, se deben proporcionar tests unitarios que validen el correcto funcionamiento de los componentes principales, particularmente la evaluación correcta de k-particiones y la consistencia con los resultados de bi-partición para el caso k=2.

## **4.2 Documentación Técnica** {#4.2-documentación-técnica}

Se debe entregar un reporte técnico comprehensivo que documente el trabajo realizado. Este reporte debe comenzar con una explicación matemática clara y rigurosa de cómo se extiende el marco teórico de GeoMIP y QNodes de bi-particiones a k-particiones. Esto incluye la formulación precisa del problema de optimización, la definición de la función de pérdida para k-particiones, y la justificación de que la tabla de costos calculada para bi-particiones es aplicable al caso k-particiones.

El reporte debe incluir una descripción detallada del enfoque algorítmico implementado, explicando las decisiones de diseño tomadas, las estructuras de datos utilizadas, y cómo se aborda el desafío de la explosión combinatoria del espacio de k-particiones. Esta descripción debe ser suficientemente detallada para que otro equipo pueda comprender el funcionamiento del algoritmo sin necesidad de leer el código fuente.

Se debe proporcionar un análisis de complejidad completo, tanto teórico como empírico. El análisis teórico debe caracterizar la complejidad temporal y espacial del algoritmo en función de n (número de variables) y k (número de particiones), identificando los cuellos de botella computacionales principales. El análisis empírico debe medir los tiempos de ejecución reales en los datasets de prueba y comparar estos tiempos con las predicciones teóricas y con los métodos de referencia.

La documentación debe incluir secciones que describan las limitaciones conocidas de la implementación, casos donde el método puede no funcionar óptimamente, posibles mejoras futuras identificadas durante el desarrollo, y lecciones aprendidas del proceso de implementación. Esta reflexión crítica sobre el trabajo realizado es fundamental para demostrar comprensión profunda del problema.

## **4.3 Resultados Experimentales** {#4.3-resultados-experimentales}

Se debe realizar una validación experimental exhaustiva utilizando los datasets de prueba proporcionados. Para sistemas pequeños donde la búsqueda exhaustiva es viable, se debe comparar las k-particiones encontradas por la implementación con las k-MIPs óptimas globales, calculando métricas de precisión como la tasa de acierto exacto y el error relativo en la pérdida de información. Para el caso particular k=2, se debe verificar que los resultados coinciden con los obtenidos por la implementación original de GeoMIP y de QNodes para bi-particiones.

Los resultados deben presentarse de forma clara y sistemática mediante tablas que resuman métricas clave como tiempos de ejecución, tasas de acierto, errores relativos y speedups obtenidos respecto a métodos de referencia. Se deben incluir gráficas que ilustren cómo estas métricas varían con el tamaño del sistema y el valor de k, permitiendo identificar patrones y tendencias en el comportamiento del algoritmo.

El análisis experimental debe ir más allá de la simple presentación de números, incluyendo interpretación de los resultados obtenidos. Esto incluye discusión sobre qué patrones se observan en las k-particiones óptimas encontradas, si existe estructura modular recurrente en los sistemas analizados, cómo cambia la partición óptima al variar k, y qué revela esto sobre la organización causal del sistema. Se debe analizar también casos donde el método encuentra soluciones subóptimas, investigando las causas y proponiendo posibles remedios.

Finalmente, si el equipo implementó múltiples variantes o estrategias alternativas del enfoque básico, se debe incluir comparación experimental entre estas variantes, analizando los trade-offs entre precisión y eficiencia, identificando qué variante funciona mejor en qué circunstancias, y proporcionando recomendaciones sobre cuándo usar cada alternativa.

## **4.4 Presentación Final** {#4.4-presentación-final}

Cada equipo debe preparar y entregar una presentación que resuma el trabajo realizado y los resultados obtenidos. La presentación tendrá una duración máxima de 15 minutos, más 5 minutos para preguntas y discusión. El contenido debe estructurarse de manera que primero se contextualice el problema y se explique la extensión teórica de bi-particiones a k-particiones, luego se presente el enfoque algorítmico desarrollado de manera clara pero concisa, se muestren los resultados experimentales más significativos mediante visualizaciones efectivas, y finalmente se discutan las conclusiones y lecciones aprendidas.

Se espera que la presentación incluya una demostración en vivo del software funcionando, ejecutando la búsqueda de k-particiones en al menos un sistema de prueba y mostrando los resultados obtenidos. Si es posible, se debe incluir visualización de las k-particiones encontradas sobre la representación del hipercubo, ilustrando cómo los k-1 hiperplanos dividen el espacio de estados. Esta componente visual ayuda a transmitir la intuición geométrica del método y hace la presentación más comprensible y memorable.

## **4.5 Criterios de Evaluación** {#4.5-criterios-de-evaluación}

La evaluación del proyecto considerará múltiples dimensiones de calidad. La correctitud de la implementación se evaluará verificando que produce resultados correctos en casos de validación, que mantiene consistencia con GeoMIP original y QNodes original para k=2, y que el código es robusto frente a diferentes inputs y casos edge. La eficiencia se medirá comparando tiempos de ejecución con métodos de referencia cuando estos sean viables, analizando la escalabilidad con n y k, y evaluando el uso efectivo de recursos computacionales.

La calidad del código se evaluará considerando la claridad y organización del código, la completitud de la documentación y comentarios, el seguimiento de las convenciones de estilo del proyecto, y la inclusión de tests que validen funcionalidad. La documentación técnica se evaluará por la claridad en la explicación de conceptos matemáticos y algorítmicos, la profundidad del análisis de complejidad, la calidad del análisis experimental y visualizaciones, y la reflexión crítica sobre limitaciones y mejoras posibles.

Finalmente, la presentación se evaluará considerando la claridad en la comunicación de ideas complejas, la efectividad de las visualizaciones utilizadas, la calidad de la demostración en vivo, y la capacidad de responder preguntas y defender decisiones de diseño. El trabajo en equipo y la distribución equitativa de responsabilidades también serán considerados en la evaluación global del proyecto.

5. # **Observaciones Finales** {#observaciones-finales}

Este proyecto representa una oportunidad para profundizar en problemas de optimización combinatoria complejos, aplicar y extender técnicas de representación geométrica de sistemas discretos, y desarrollar soluciones algorítmicas eficientes para problemas con relevancia teórica en el campo de la cuantificación de información integrada y la teoría de la conciencia.

El desafío principal radica en diseñar enfoques que balanceen adecuadamente la necesidad de encontrar particiones de alta calidad con la restricción de hacerlo en tiempos computacionales razonables. Este balance requiere creatividad algorítmica, comprensión profunda de las propiedades matemáticas del problema, y capacidad para identificar y explotar estructura en el espacio de soluciones.

El trabajo desarrollado en este proyecto contribuirá a extender las capacidades de análisis de sistemas complejos más allá de las bi-particiones tradicionales, abriendo nuevas posibilidades para investigar la estructura modular y las dependencias causales en sistemas con múltiples niveles de organización. Los métodos y conocimientos adquiridos tendrán aplicabilidad no solo en el contexto específico de IIT, sino más generalmente en problemas de clustering, detección de comunidades, y análisis de redes donde la identificación de particiones óptimas juega un papel fundamental.