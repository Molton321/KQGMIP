***Universidad de Caldas***

**ESPECIFICACIONES DE ENTREGABLES**

Proyecto K-QGMIP: Manual Técnico 

*Análisis y Diseño de Algoritmos*

*Facultad de Inteligencia Artificial e Ingenierías*

*2026-1*

# **Introducción**

Como parte integral del proyecto K-QGMIP, cada equipo debe entregar documentación técnica completa que permita comprender el trabajo desarrollado. Esta documentación se refiere al Manual Técnico, que trata los aspectos algorítmicos y de implementación del proyecto.

La calidad de la documentación es un criterio de evaluación fundamental, ya que refleja la profundidad de comprensión del problema, la capacidad de comunicar las estrategias complejas de manera efectiva, y la claridad con la que se aborda el desarrollo de software. Un buen proyecto se refuerza con documentación clara, completa y efectiva que potencia significativamente el impacto del trabajo realizado.

Este documento especifica en detalle los requisitos, estructura y contenido que deben tener este manual. 

# **Convenciones de Nomenclatura**

Para mantener consistencia y facilitar la organización del código, se establecen las siguientes convenciones de nomenclatura para los repositorios y carpetas del proyecto:

| Estrategia | Nombre de Repositorio/Carpeta |
| :---- | :---- |
| **GeoMIP K-particiones** | **KGeoMIP** |
| **QNodes K-particiones** | **KQNodes** |

Estas convenciones deben aplicarse consistentemente en:

* Nombre del repositorio Git  
* Carpeta principal del proyecto  
* Nombre de la clase principal que implementa la estrategia  
* Referencias en documentación y presentaciones

La 'K' inicial hace referencia a 'k-particiones', distinguiendo claramente estas extensiones de las implementaciones originales de bi-particiones (GeoMIP y QNodes).

#  **Manual Técnico**

## **1 Propósito**

El Manual Técnico está orientado a la comprension  de los aspectos algorítmicos, matemáticos e implementación del proyecto. Este documento debe permitir tener un panorama claro del software desarrollado y/o modificado, asi como la estructura del mismo.

## **2 Estructura y Contenido Requerido**

### **2.1 Resumen Ejecutivo**

Aqui se debe incluir:

* Descripción concisa del problema abordado y su relevancia  
* Enfoque algorítmico implementado en términos generales  
* Principales resultados obtenidos y contribuciones del proyecto  
* Limitaciones encontradas y recomendaciones de uso

### **2.2 Fundamentos Teóricos**

Esta sección debe proporcionar la base matemática y conceptual necesaria para comprender el proyecto. Contenido requerido:

* **Definición formal de k-particiones:** Notación matemática precisa, propiedades fundamentales, y ejemplos ilustrativos para casos pequeños (n=3 o n=4).  
* **Formulación del problema de optimización:** Función o funciones objetivo a optimizar , restricciones del problema.  
* **Extensión del marco teórico:** Explicación clara de cómo se extiende el marco de GeoMIP y/o QNodes de bi-particiones a k-particiones. Justificación deque sus estrategias son aplicables y que obtienen una “buena” respuesta.  
* **Análisis de complejidad del espacio de soluciones:** Análisis del crecimiento del problema  y comparación con el caso de bi-particiones.

### **2.3 Arquitectura del Software**

Descripción comprehensiva de la arquitectura del sistema implementado. Esta sección es fundamental para comprender la organización del código y facilitar futuras extensiones. Debe incluir:

* **Diagrama de Arquitectura General:** Representación visual de los componentes principales del sistema y sus interrelaciones. Mostrar cómo se integra la extensión k-particiones con la infraestructura existente del proyecto.  
* **Diagrama de Clases:** Diagrama UML mostrando:  
  * Clase base SIA y su relación de herencia con KGeoMIP y KQNodes  
  * Clases auxiliares y estructuras de datos (N-Cubos, gestores de particiones, etc.)  
  * Atributos principales de cada clase con sus tipos  
  * Métodos públicos y privados más importantes  
  * Relaciones de composición, agregación y dependencia

* **Diagrama de Paquetes:** Organización modular del código mostrando:  
  * Estructura de directorios del proyecto (src/controllers/strategies/, src/models/, src/utils/, etc.)  
  * Dependencias entre paquetes y módulos  
  * Ubicación de archivos de configuración, tests, y documentación

* **Diagrama de Secuencia:** Uno o más diagramas UML de secuencia mostrando el flujo de ejecución para casos de uso principales:  
  * Inicialización del sistema y carga de datos  
  * Búsqueda de k-MIP para un valor específico de k  
  * Evaluación de una k-partición candidata  
  * Interacción entre componentes principales durante la ejecución

* **Patrones de Diseño Aplicados:** Identificación y justificación de patrones de diseño utilizados (Strategy, Template Method, Factory, etc.) y cómo facilitan la extensibilidad y mantenibilidad del código.  
* **Decisiones Arquitectónicas Clave:** Explicación de decisiones importantes de diseño tomadas, como por ejemplo: Estrategia de reutilización de componentes existentes (o si se reimplementaron), trade-offs considerados entre flexibilidad y rendimiento, separación de responsabilidades entre componentes etc.

***Observación:** Todos los diagramas deben ser claros, legibles y seguir notación UML estándar.* 

### **2.4 Diseño Algorítmico**

Descripción detallada del enfoque algorítmico implementado. Esta es la sección central del manual técnico y debe permitir reproducir el algoritmo. Debe incluir:

* **Visión general del algoritmo:** Descripción en alto nivel del enfoque, filosofía de diseño, y cómo se relaciona con las estrategias GeoMIP y QNodes originales.  
* **Pseudocódigo detallado:** Algoritmos principales y subrutinas clave presentados en pseudocódigo claro y bien comentado. Usar notación consistente con la sección de fundamentos teóricos.  
* **Estructuras de datos:** Descripción de las estructuras de datos utilizadas (N-Cubos, tabla de costos, representación de particiones, etc.), justificación de elecciones de diseño, y diagramas cuando sea apropiado.  
* **Estrategia de búsqueda:** Explicación detallada de cómo se genera y explora el espacio de k-particiones candidatas. Técnicas de diseño empleadas (PD, DyV, voraz, B\&B, aproximados, etc).Si se utilizan  heurísticas, describir su funcionamiento y justificación.  
* **Evaluación de particiones:** Procedimiento para calcular la pérdida de información de una k-partición candidata.  
* **Optimizaciones implementadas:** Técnicas específicas para mejorar eficiencia (caching, paralelización, etc.)

### **2.5 Análisis de Complejidad**

Análisis teórico riguroso de la complejidad computacional del algoritmo:

* **Complejidad temporal:** Expresión usando cotas asintóticas fuertes usando  la notación asintótica en función de n (número de variables) y k (número de particiones). Identificar operaciones dominantes y cuellos de botella.  
* **Complejidad espacial:** Análisis del uso de memoria, considerando estructuras de datos permanentes y temporales.  
* **Análisis de casos:** Mejor caso y peor caso. Identificar qué características del sistema o valor de k conducen a cada caso.  
* **Comparación con alternativas:** Contrastar la complejidad con búsqueda exhaustiva, o la fuerza bruta y con las estrategias originales para bi-particiones.

### **2.6 Detalles de Implementación**

Aspectos específicos de la implementación en el lenguaje de programación utilizado (Python):

* **Métodos principales:** Descripción de la funcionalidad de cada método público importante, incluyendo firmas de función, parámetros, valores de retorno y excepciones.  
* **Dependencias externas:** Bibliotecas utilizadas (NumPy, SciPy, etc.), versiones requeridas, y para que su uso.  
* **Aspectos de ingeniería de software:** Manejo de errores, logging, validación de inputs, y estrategias para debugging.  
* **Tests implementados:** Descripción de tests unitarios y de integración, casos de prueba específicos, y estrategia de validación.

### **2.7 Resultados Experimentales**

Presentación  de resultados obtenidos en evaluación experimental:

* **Datasets utilizados:** Descripción de sistemas de prueba, características relevantes (tamaño, origen, etc.).  
* **Métricas de evaluación:** Definición clara de métricas utilizadas (tiempo de ejecución, tasa de acierto, error relativo, speedup, etc.).  
* **Tablas de resultados:** Tablas bien formateadas con resultados numéricos para diferentes combinaciones de n y k. Incluir desviaciones estándar donde sea apropiado.  
* **Gráficas y visualizaciones:** Gráficos de escalabilidad (tiempo vs n, tiempo vs k), curvas de precisión, visualizaciones de k-particiones encontradas sobre hipercubos, y comparaciones con métodos baseline.  
* **Análisis de resultados:** Interpretación de patrones observados, discusión de casos donde el algoritmo funciona mejor/peor, y comparación entre estrategias KGeoMIP y KQNodes.  
* **Validación de correctitud:** Evidencia de que los resultados son correctos, incluyendo comparación con búsqueda exhaustiva para casos pequeños y verificación de consistencia para k=2.

### **2.8 Limitaciones y Trabajo Futuro**

Reflexión crítica sobre el trabajo realizado:

* **Limitaciones conocidas:** Restricciones del enfoque actual, casos donde no funciona óptimamente, y limitaciones de escalabilidad.  
* **Supuestos y restricciones:** Suposiciones hechas durante el desarrollo que podrían no cumplirse en todos los contextos.  
* **Mejoras potenciales:** Ideas específicas para optimizar el algoritmo, extender funcionalidad, o mejorar robustez.  
* **Direcciones de investigación futura:** Preguntas abiertas y extensiones interesantes del trabajo actual.

### **2.9 Apéndices Técnicos**

Material complementario que apoya el documento principal:

* **Demostracioness:** Pruebas detalladas de proposiciones mencionadas en el texto principal pero cuyo desarrollo completo interrumpiría el flujo.  
* **Detalles algorítmicos adicionales:** Pseudocódigo de funciones auxiliares, optimizaciones menores, o variantes exploradas.  
* **Resultados experimentales de las pruebas:** Tablas completas de resultados, experimentos adicionales no incluidos en el cuerpo principal, y análisis de sensibilidad de parámetros.  
* **Referencias y bibliografía:** Lista completa de artículos, libros y recursos consultados, con formato académico apropiado.

## **3 Características de Formato y Presentación**

El Manual Técnico debe cumplir con los siguientes estándares de formato:

* **Formato:** Documento PDF o Word, tamaño carta,  fuente Arial o Times New Roman de 11 puntos.  
* **Ecuaciones y notación matemática:** Por faaaaavor usar editores de ecuaciones apropiados (LaTeX, MathType, o el editor de ecuaciones de Word). Mantener notación consistente en todo el documento.  
* **Diagramas UML:** Todos los diagramas deben seguir notación UML 2.x estándar. Usar colores moderadamente para mejorar legibilidad. Cada diagrama o figura en el documento  debe estar numerado y tener título descriptivo.  
* **Figuras y tablas:** Todas numeradas secuencialmente, con títulos descriptivos. Incluir referencias en el texto. Verificar la calidad de la imagen, que sea  apropiada para su revisión.  
* **Código y pseudocódigo:** Usar fuente monoespaciada (Courier New, Consolas), con sangrado consistente y resaltado de sintaxis cuando sea posible.  
* **Organización:** Tabla de contenidos al inicio, numeración de secciones clara, encabezados distintivos, y páginas numeradas.  
* **Calidad de redacción:** Lenguaje técnico preciso, gramática y ortografía correctas, argumentación lógica, coherente, y claridad expositiva.

## **4 Uso de Inteligencia Artificial Generativa**

# Es importante documentar de manera transparente el uso de herramientas de IA generativa (ChatGPT, Claude, GitHub Copilot, etc.) durante el desarrollo del proyecto. Si se utilizaron estas herramientas, se debe incluir una subsección que especifique: qué herramientas se utilizaron y en qué etapas del proyecto (diseño de algoritmos, implementación, debugging, optimización, documentación), ejemplos específicos de prompts o consultas realizadas y cómo influyeron en decisiones de diseño, qué partes del código o pseudocódigo fueron generadas o significativamente influenciadas por IA, y una reflexión crítica sobre las ventajas y limitaciones encontradas al usar estas herramientas. Esta documentación no afecta negativamente la evaluación; por el contrario, demuestra profesionalismo, honestidad académica y capacidad de usar herramientas modernas de manera efectiva. Lo que se evalúa es la comprensión profunda del trabajo realizado y la capacidad de justificar decisiones algorítmicas, independientemente de las herramientas utilizadas para llegar a ellas.

# 

