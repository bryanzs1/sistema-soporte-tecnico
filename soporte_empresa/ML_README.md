# Sistema Inteligente de Clasificación de Tickets 🤖

## Descripción General

Este sistema utiliza **Machine Learning** para asignar automáticamente tickets a los técnicos más apropiados basándose en:

- 📝 **Contenido del ticket**: Análisis del título y descripción usando NLP (Natural Language Processing)
- 🏷️ **Categoría y prioridad**: Considera el tipo de problema y su urgencia
- 👨‍💻 **Experiencia del técnico**: Evalúa el rendimiento histórico, especialización y tiempo de resolución

## ¿Cómo Funciona?

### 1. Entrenamiento del Modelo

El modelo se entrena con tickets históricos (cerrados) que incluyen:
- Título y descripción del ticket
- Categoría y prioridad
- Técnico que lo resolvió
- Tiempo de resolución
- Calificación de satisfacción (opcional)

**Requisitos mínimos**: 10 tickets cerrados

### 2. Predicción Automática

Cuando se crea un nuevo ticket:
1. El sistema analiza el contenido usando **TF-IDF** (Term Frequency-Inverse Document Frequency)
2. Combina características de texto con categoría y prioridad
3. El modelo **Random Forest** predice el técnico más adecuado
4. Calcula un **puntaje de confianza** (0-100%)
5. Si la confianza es **>70%**, auto-asigna el ticket

### 3. Mejora Continua

- El modelo aprende de cada ticket resuelto
- Las estadísticas de técnicos se actualizan continuamente
- Se puede reentrenar el modelo periódicamente para mejorar la precisión

## Características Principales

### ✅ Asignación Inteligente
- Sugerencias basadas en ML, no reglas fijas
- Considera múltiples factores simultáneamente
- Aprende patrones de asignación exitosos

### 📊 Estadísticas de Técnicos
- Tickets resueltos
- Tiempo promedio de resolución
- Calificación de satisfacción promedio
- Especialización por categoría

### 🎯 Precisión Medible
- Seguimiento de predicciones vs asignaciones reales
- Métricas de precisión del modelo
- Historial de predicciones recientes

## Uso del Sistema

### Interfaz Web (Administrador)

1. **Acceder al Sistema ML**
   - Dashboard → "🤖 ML Classification System"

2. **Entrenar el Modelo**
   - Primera vez: Click en "Train Model Now"
   - Reentrenar: Click en "Retrain Model"

3. **Monitorear Rendimiento**
   - Ver precisión del modelo
   - Revisar estadísticas de técnicos
   - Analizar predicciones recientes

### Comandos CLI

```bash
# Entrenar el modelo
flask ml-train

# Ver información del modelo
flask ml-info

# Ver estadísticas de técnicos
flask ml-stats
```

## Arquitectura Técnica

### Tecnologías
- **scikit-learn**: Framework de Machine Learning
- **NumPy**: Computación numérica
- **TfidfVectorizer**: Procesamiento de texto
- **RandomForestClassifier**: Algoritmo de clasificación

### Almacenamiento
- Modelos entrenados: `ml_models/ticket_classifier.pkl`
- Estadísticas: Tabla `technician_stats` en PostgreSQL

### Flujo de Datos

```
Ticket Nuevo
    ↓
Extracción de características (TF-IDF + categoría + prioridad)
    ↓
Predicción del modelo (Random Forest)
    ↓
Cálculo de confianza + ajuste por rendimiento del técnico
    ↓
Sugerencia/Auto-asignación
```

## Campos Agregados a la Base de Datos

### Tabla `ticket`
- `resolution_time_minutes`: Tiempo de resolución en minutos
- `satisfaction_rating`: Calificación 1-5 (opcional)
- `ml_suggested_technician_id`: Técnico sugerido por ML
- `ml_confidence_score`: Confianza de la predicción (0-1)
- `auto_assigned`: Indica si fue asignado automáticamente

### Tabla `technician_stats` (nueva)
- `technician_id`: ID del técnico
- `total_tickets_resolved`: Total de tickets resueltos
- `avg_resolution_time`: Tiempo promedio en minutos
- `avg_satisfaction`: Calificación promedio
- `specialization`: Categorías donde es experto (JSON)
- `last_updated`: Última actualización

## Mejores Prácticas

### Entrenamiento
- ✅ Reentrenar el modelo cada 2-4 semanas
- ✅ Esperar tener al menos 50 tickets para buena precisión
- ✅ Monitorear la precisión después de cada entrenamiento

### Uso Diario
- Los tickets se auto-asignan solo con alta confianza (>70%)
- Revisar sugerencias ML en tickets no asignados
- Actualizar manualmente si el ML no se ajusta al contexto específico

### Mejora de Precisión
- Mantener datos de calidad (categorías y prioridades consistentes)
- Cerrar tickets cuando estén realmente resueltos
- Agregar calificaciones de satisfacción cuando sea posible

## Limitaciones Conocidas

1. **Datos mínimos**: Requiere al menos 10 tickets cerrados para entrenar
2. **Nuevos técnicos**: No puede sugerir técnicos sin historial de tickets
3. **Contexto específico**: No entiende información fuera del texto del ticket
4. **Idioma**: Actualmente optimizado para español e inglés

## Roadmap Futuro

- [ ] Embeddings de transformers (BERT) para mejor comprensión de texto
- [ ] Predicción de tiempo de resolución
- [ ] Recomendaciones de categoría/prioridad automáticas
- [ ] Detección de tickets duplicados
- [ ] API para integración con otros sistemas

## Soporte

Para reportar problemas o sugerir mejoras, contacta al administrador del sistema.

---

**Desarrollado con ❤️ usando Flask + scikit-learn**
