# Sistema de Soporte Técnico - Asistente Inteligente Flotante

## 🤖 Características Nuevas: Asistente Conversacional Inteligente

El asistente de soporte ahora incluye capacidades de conversación natural impulsadas por LLM (Large Language Models) con inteligencia integrada para resolución de problemas técnicos.

### 🎯 Cómo Funciona

El asistente utiliza una **cadena de fallback inteligente** para proporcionar las mejores respuestas:

```
Mensaje del Usuario
        ↓
┌─────────────────────────────┐
│ 1. Intenta API de LLM      │
│    (Groq o OpenAI)          │
└─────────────────────────────┘
        ↓
   ¿Respuesta?
   Sí → Enviar respuesta
   ¿No configurado?
        ↓
┌─────────────────────────────┐
│ 2. Fallback: Base de Conocimientos │
│    (7 categorías predefinidas)│
└─────────────────────────────┘
        ↓
   ¿Coincidencia encontrada?
   Sí → Enviar respuesta + sugerir ticket
   No → Respuesta por defecto + sugerir crear ticket
```

### 🔑 Características Clave

1. **Memoria de Conversación**
   - El asistente recuerda hasta 20 mensajes por usuario
   - La memoria expira después de 1 hora de inactividad
   - Contexto se utiliza para respuestas más relevantes

2. **Sistema de Prompts Multiidioma**
   - Prompts en español e inglés que refuerzan enfoque técnico
   - Restricción automática: solo responde sobre temas técnicos
   - Sigue instrucciones de profesionalismo

3. **Fallback Inteligente**
   - Si LLM falla o no está configurado → usa base de conocimientos
   - Si no hay coincidencia en KB → respuesta por defecto con invitación a crear ticket
   - Cada respuesta incluye score de confianza

4. **Integración con Sistema de Tickets**
   -Cuando el asistente no puede resolver, sugiere crear ticket
   - Prefill automático de título, descripción y categoría
   - Usuario puede revisary enviar directamente

### 🚀 Configuración de LLM (Opcional)

El asistente funciona **sin API de LLM**, pero activa capacidades de conversación normal con la configuración:

#### Opción 1: Groq API (RECOMENDADO - Gratis)

1. Registrate en https://console.groq.com
2. Genera API Key en https://console.groq.com/keys
3. En `.env`, agrega:
   ```bash
   GROQ_API_KEY=tu-clave-aqui
   ```

**Ventajas:**
- Completamente gratis
- Generoso límite de tasa (500 req/min)
- Modelo muy capaz: Mixtral 8x7B

#### Opción 2: OpenAI API (Fallback pagado)

1. Registrate en https://platform.openai.com
2. Genera API Key en https://platform.openai.com/api-keys
3. En `.env`, agrega:
   ```bash
   OPENAI_API_KEY=sk-...
   ```

**Ventajas:**
- Muy confiable
- Modelo más poderoso (GPT-3.5-turbo)
- Usado como fallback si Groq no está disponible

### 📊 Comportamiento sin API de LLM

Si no configuras ninguna API de LLM, el asistente:
- ✅ Sigue siendo completamente funcional
- ✅ Usa el sistema de base de conocimientos (KB)
- ✅ Puede crear tickets con contexto
- ❌ No tiene memoriade conversación
- ❌ Responde solo en base a coincidencias de palabras clave

### 🧠 Categorías de la Base de Conocimientos

El asistente puede categorizar automáticamente problemas en:

1. **Accesos y cuentas** - Contraseñas, inicio de sesión, 2FA
2. **Impresoras** - Configuración, drivers, errores
3. **VPN y conectividad remota** - Conexiones, desconexiones
4. **Rendimiento del sistema** - Lentitud, congelación
5. **Software y aplicaciones** - Instalación, bugs
6. **Correo electrónico** - Configuración, sincronización
7. **Hardware y periféricos** - Monitores, teclados, etc.

### 📝 Ejemplos de Uso

#### Con LLM configurado:
```
Usuario: "Mi laptop se congela cada vez que abro Photoshop"
Asistente: [Usa LLM para dar pasos detallados de troubleshooting]
→ Respuesta natural y conversacional

Usuario: "Ya intenté reiniciar, ¿qué más puedo hacer?"
Asistente: [Recuerda contexto anterior, da siguiente paso]
→ Conversación como ChatGPT, pero enfocada en tech
```

#### Sin LLM (fallback KB):
```
Usuario: "No puedo conectarme a la VPN"
Asistente: [Detecta categoría VPN]
→ Proporciona respuesta predefinida útil
→ Sugiere crear ticket si necesita ayuda personalizada
```

### ✅ Testing

Para verificar que todo funciona:

**En el navegador:**
1. Abre la app autenticado
2. Haz clic en el botón azul inferior derecho "Support Assistant"
3. Escribe un problema técnico
4. El asistente debe responder

**Pruebas de idioma:**
- Español: "No puedo conectarme a la VPN" → categoría 'VPN' ✓
- Inglés: "I forgot my password" → categoría 'Accesos' ✓
- Español: "Mi impresora no imprime" → categoría 'Impresoras' ✓

### 🔒 Seguridad

- Las API keys se almacenan en variables de entorno (NUNCA en código)
- Las conversaciones se guardan en memoria del servidor (temporal)
- Se limpian automáticamente después de 1 hora
- Las claves de API (GROQ_API_KEY, OPENAI_API_KEY) no se registran en logs

### 📈 Monitoreo

El asistente registra:
- Llamadas fallidas a LLM (con error genérico sin exponer secretos)
- Cuándo se usa fallback a KB
- Respuestas por defecto (asistente no supo responder)

Ver logs:
```bash
tail -f app.log | grep "ai_chatbot"
```

### 🐛 Troubleshooting

**P: El asistente no responde**
- Verifica que el usuario esté autenticado
- Asegúrate de que el mensaje tenga al menos 3 caracteres

**P: LLM no funciona (pero sigue respondiendo)**
- Verifica que `GROQ_API_KEY` o `OPENAI_API_KEY` estén en `.env`
- Revisa que la clave sea válida en la consola del proveedor
- Mira los logs: `grep "API error" app.log`
- El sistema fallback automáticamente a KB - es normal

**P: Respuestas lentas**
- LLM tarda 1-3 segundos
- KB es instantáneo
- Considera usar Groq (más rápido que OpenAI)

**P: Memoria no persiste entre sesiones**
- Es correcto: memorias por usuario en servidor, temporal
- Se limpia después de 1 hora
- Para persistencia permanente, implementaria una tabla de BD

### 🚀 Deployment en Render

El código fue desplegado automáticamente a Render en commit `9f6d15e`.

Próximos pasos en Render:
1. Verifica que la app se re-desplegó (espera 2-3 min)
2. Copia tu API key de Groq/OpenAI
3. En Render Dashboard → Environment:
   ```
   GROQ_API_KEY = tu-clave-aqui
   ```
4. Renderredeplairá automáticamente con la nueva variable

### 📚 Recursos

- [Groq Docs](https://console.groq.com/docs)
- [OpenAI API Docs](https://platform.openai.com/docs)
- [Sistema de Tickets Integrado](./README.md#tickets)

---

**Versión**: 2.0 (con inteligencia conversacional)
**Fecha**: Marzo 20, 2026
**Estado**: En producción en Render
