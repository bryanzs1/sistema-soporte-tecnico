"""AI-powered chatbot for automatic responses to common issues.

Provides automatic answers to frequently asked questions and common problems.
"""

import logging
import unicodedata
from typing import Dict, Optional, List
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

# Conversation memory: {user_id: [{'role': 'user'|'assistant', 'content': str, 'timestamp': datetime}, ...]}
_conversation_history = {}
_MAX_HISTORY_LENGTH = 20
_HISTORY_TIMEOUT = 3600  # 1 hour

def _cleanup_old_conversations():
    """Remove conversations older than timeout."""
    now = datetime.utcnow()
    for user_id, messages in list(_conversation_history.items()):
        if messages and (now - messages[-1].get('timestamp', now)).total_seconds() > _HISTORY_TIMEOUT:
            del _conversation_history[user_id]

def get_conversation_history(user_id: int) -> List[Dict]:
    """Get conversation history for a user, cleaned up."""
    _cleanup_old_conversations()
    return _conversation_history.get(user_id, [])

def add_to_conversation(user_id: int, role: str, content: str):
    """Add a message to conversation history."""
    if user_id not in _conversation_history:
        _conversation_history[user_id] = []
    
    _conversation_history[user_id].append({
        'role': role,
        'content': content,
        'timestamp': datetime.utcnow(),
    })
    
    # Keep only recent messages
    if len(_conversation_history[user_id]) > _MAX_HISTORY_LENGTH:
        _conversation_history[user_id] = _conversation_history[user_id][-_MAX_HISTORY_LENGTH:]

def _build_system_prompt(lang: str) -> str:
    """Build system prompt for technical support assistant."""
    if lang == 'es':
        return """Eres un asistente técnico de soporte profesional para empresas. 
Tu rol es ayudar a empleados a resolver problemas técnicos de IT.

IMPORTANTE:
- Responde SOLO sobre temas técnicos: redes, hardware, software, contraseñas, VPN, impresoras, etc.
- Sé conciso y útil. Proporciona pasos claros para resolver problemas.
- Si es un problema que no puedas resolver fácilmente, sugiere crear un ticket.
- Responde siempre en español.
- Usa lenguaje profesional pero amable."""
    else:
        return """You are a professional technical support assistant for companies.
Your role is to help employees resolve IT technical problems.

IMPORTANT:
- Respond ONLY about technical topics: networks, hardware, software, passwords, VPN, printers, etc.
- Be concise and helpful. Provide clear steps to resolve problems.
- If it's a problem you can't easily resolve, suggest creating a support ticket.
- Always respond in English.
- Use professional but friendly language."""

# Knowledge base of common issues and solutions.
# Each entry supports English and Spanish so the same assistant can work in
# both languages without relying on external translation services.

KNOWLEDGE_BASE = [
    {
        'id': 1,
        'keywords_en': ['password', 'login', 'access', 'forgot', 'reset', 'locked', 'account', 'forgot password', 'cannot log in', 'reset password'],
        'keywords_es': ['contrasena', 'contraseña', 'acceso', 'ingreso', 'login', 'olvide', 'restablecer', 'bloqueado', 'cuenta', 'no puedo entrar', 'recuperar clave'],
        'category': 'Account',
        'ticket_category': 'Accesos y cuentas',
        'response_en': """I can help you reset your password!

**Quick steps:**
1. Go to the login page
2. Click "Forgot password?"
3. Enter your email
4. Check your inbox for reset link
5. Create a new password

**Still having issues?** Reply to this ticket and a technician will help you within 30 minutes.""",
        'response_es': """Puedo ayudarte a restablecer tu contraseña.

**Pasos rápidos:**
1. Ve a la pantalla de inicio de sesión
2. Haz clic en "¿Olvidaste tu contraseña?"
3. Ingresa tu correo
4. Revisa tu bandeja de entrada para el enlace
5. Crea una nueva contraseña

**Si el problema continúa:** crea un ticket y un técnico te ayudará lo antes posible.""",
        'category_slug': 'account_access',
        'confidence_min': 0.5,
    },
    {
        'id': 2,
        'keywords_en': ['printer', 'printing', 'print', 'not printing', 'paper', 'toner'],
        'keywords_es': ['impresora', 'imprimir', 'impresion', 'impresión', 'no imprime', 'papel', 'toner', 'tinta', 'no puedo imprimir', 'error de impresora'],
        'category': 'Hardware',
        'ticket_category': 'Impresoras',
        'response_en': """Let me help with your printer issue!

**Try these steps first:**
1. Check if printer is powered on (green light)
2. Verify paper is loaded in tray
3. Check for paper jams - open all panels
4. Restart printer (off for 30 seconds, then on)
5. On your computer: Settings > Devices > Printers > Reset printer

**If still not working:**
- Tell us the printer model
- What error message do you see?
- A technician will check remotely""",
    'response_es': """Voy a ayudarte con el problema de impresión.

**Prueba primero esto:**
1. Verifica que la impresora esté encendida
2. Confirma que tenga papel en la bandeja
3. Revisa si hay atasco de papel
4. Reinicia la impresora durante 30 segundos
5. En tu equipo vuelve a seleccionar o reiniciar la impresora

**Si sigue fallando:** indícame el modelo y el error que aparece para abrir el ticket mejor clasificado.""",
        'category_slug': 'hardware_printer',
        'confidence_min': 0.7,
    },
    {
        'id': 3,
    'keywords_en': ['wifi', 'internet', 'network', 'connection', 'connected', 'not connecting'],
    'keywords_es': ['wifi', 'internet', 'red', 'conexion', 'conexión', 'sin internet', 'no conecta', 'no tengo red', 'no hay internet', 'problema de red'],
        'category': 'Network',
    'ticket_category': 'Red',
    'response_en': """I can help with your network connection!

**Quick troubleshooting:**
1. Restart your router (unplug 30 seconds)
2. Unplug/replug ethernet cable if wired
3. Forget WiFi network and reconnect
4. Move closer to router
5. Restart your device

**Network info needed:**
- Are you wired or WiFi?
- Can you see the network?
- Do other devices work?

A technician will investigate if needed.""",
    'response_es': """Puedo ayudarte con el problema de red.

**Diagnóstico rápido:**
1. Reinicia el router o punto de acceso
2. Si usas cable, desconéctalo y vuelve a conectarlo
3. Olvida la red WiFi y vuelve a conectarte
4. Acércate al router si estás por WiFi
5. Reinicia tu equipo

**Para escalarlo mejor:** dime si usas cable o WiFi y si otros equipos sí tienen conexión.""",
        'category_slug': 'network_wifi',
        'confidence_min': 0.65,
    },
    {
        'id': 4,
    'keywords_en': ['slow', 'lag', 'frozen', 'sluggish', 'hang', 'performance'],
    'keywords_es': ['lento', 'lentitud', 'congelado', 'trabado', 'se cuelga', 'rendimiento', 'muy lento', 'mi computadora esta lenta', 'mi computadora está lenta'],
        'category': 'Software',
    'ticket_category': 'Software',
    'response_en': """Your device is running slowly? Let's speed it up!

**Quick fixes:**
1. Restart your computer (save work first)
2. Close unnecessary programs/browsers
3. Check Task Manager/Activity Monitor - high CPU/RAM use?
4. Clear browser cache and cookies
5. Disable browser extensions

**If still slow:**
- Tell us what programs you use
- When did slowness start?
- Any error messages?

Technician can run diagnostics if needed.""",
    'response_es': """Si tu equipo está lento, empecemos por lo básico.

**Acciones rápidas:**
1. Reinicia el equipo
2. Cierra programas o pestañas que no necesites
3. Revisa si el CPU o la memoria están saturados
4. Limpia caché del navegador si el problema es web
5. Desactiva extensiones innecesarias

**Si sigue igual:** dime qué aplicación falla y desde cuándo notas la lentitud.""",
        'category_slug': 'performance_slow',
        'confidence_min': 0.7,
    },
    {
        'id': 5,
    'keywords_en': ['software', 'install', 'download', 'app', 'program', 'license'],
    'keywords_es': ['software', 'instalar', 'instalacion', 'instalación', 'descargar', 'aplicacion', 'aplicación', 'programa', 'licencia', 'no puedo instalar', 'activar licencia'],
        'category': 'Software',
    'ticket_category': 'Software',
    'response_en': """Need software installed or licensed?

**What we can help with:**
- Installing approved company software
- License activation issues
- Microsoft Office, Adobe, etc.
- Company-approved tools

**Please provide:**
- Exact software name
- Company approval/request number (if applicable)
- What problem you're seeing

⚠️ **Security note:** Only install software approved by IT
""",
    'response_es': """Si necesitas instalar software o activar una licencia, puedo orientarte.

**Qué debemos confirmar:**
- Nombre exacto del software
- Si tiene aprobación interna
- Qué error aparece o en qué paso falla

**Importante:** solo debe instalarse software aprobado por TI. Si quieres, te dejo el ticket ya prellenado con esta información.""",
        'category_slug': 'software_install',
        'confidence_min': 0.65,
    },
    {
        'id': 6,
    'keywords_en': ['email', 'outlook', 'gmail', 'send', 'receive', 'not receiving'],
    'keywords_es': ['correo', 'outlook', 'gmail', 'enviar', 'recibir', 'no recibo', 'no llegan correos', 'correo corporativo', 'no puedo enviar correos', 'no puedo recibir correos'],
        'category': 'Software',
    'ticket_category': 'Correo corporativo',
    'response_en': """Having email trouble?

**Try these steps:**
1. Restart Outlook/email app
2. Check internet connection first
3. Verify password is correct
4. Check Junk folder
5. For Outlook: File > Account Settings > Update Password

**Tell us:**
- Gmail, Outlook, or other?
- Can you send/receive/both not working?
- Any error codes shown?

Technician can reset credentials if needed.""",
    'response_es': """Si tienes problemas con el correo, revisa esto primero.

**Pasos iniciales:**
1. Reinicia Outlook o tu cliente de correo
2. Verifica que tengas conexión a internet
3. Confirma que la contraseña siga siendo válida
4. Revisa correo no deseado
5. Si usas Outlook, actualiza la contraseña de la cuenta

**Para ayudarte mejor:** dime si no puedes enviar, recibir o ambas cosas.""",
        'category_slug': 'email_issues',
        'confidence_min': 0.7,
    },
    {
        'id': 7,
    'keywords_en': ['vpn', 'remote', 'access', 'connection', 'cannot access'],
    'keywords_es': ['vpn', 'remoto', 'acceso remoto', 'conexion remota', 'conexión remota', 'no puedo acceder', 'no puedo conectarme a la vpn', 'no conecta la vpn', 'problema con vpn'],
        'category': 'Network',
    'ticket_category': 'VPN y conectividad remota',
    'response_en': """Having trouble with VPN or remote access?

**Check first:**
1. Internet connection working?
2. Restart VPN app/client
3. Try to reconnect to service
4. Check VPN credentials
5. Try different network (home/office WiFi/wired)

**Information needed:**
- What VPN or service?
- Error message shown?
- Desktop or laptop?

A technician can verify your account access.""",
    'response_es': """Si tienes problemas con la VPN o el acceso remoto, empieza por aquí.

**Valida primero:**
1. Que tu internet funcione
2. Reinicia la aplicación VPN
3. Intenta reconectarte
4. Verifica tus credenciales
5. Si puedes, prueba otra red

**Cuando lo escales:** incluye el mensaje de error, el nombre del servicio y si usas laptop o desktop.""",
        'category_slug': 'vpn_remote',
        'confidence_min': 0.5,
    },
]


class ChatBot:
    """AI chatbot for automatic ticket responses."""
    
    def __init__(self):
        """Initialize chatbot with knowledge base."""
        self.knowledge_base = KNOWLEDGE_BASE
        self.vectorizer = None
        self.tfidf_matrix = None
        self._train()
    
    def _train(self):
        """Train TF-IDF vectorizer on knowledge base."""
        try:
            kb_texts = [self._entry_text(entry) for entry in self.knowledge_base]
            
            if kb_texts:
                self.vectorizer = TfidfVectorizer(
                    lowercase=True,
                    analyzer='char',
                    ngram_range=(2, 3),
                    min_df=1
                )
                self.tfidf_matrix = self.vectorizer.fit_transform(kb_texts)
                logger.info(f"ChatBot trained on {len(self.knowledge_base)} knowledge base entries")
        except Exception as e:
            logger.warning(f"Error training ChatBot: {e}")

    def _entry_text(self, entry: Dict) -> str:
        keywords = entry.get('keywords_en', []) + entry.get('keywords_es', [])
        category_tokens = [
            entry.get('category', ''),
            entry.get('ticket_category', ''),
            entry.get('category_slug', ''),
        ]
        return ' '.join(token for token in keywords + category_tokens if token)

    def _localized_response(self, entry: Dict, lang: str) -> str:
        if lang == 'es':
            return entry.get('response_es') or entry.get('response_en', '')
        return entry.get('response_en') or entry.get('response_es', '')

    def _normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize('NFKD', (text or '').lower())
        return ''.join(ch for ch in normalized if not unicodedata.combining(ch))

    def _build_answer(self, entry: Dict, lang: str, confidence: float) -> Dict:
        return {
            'answer': self._localized_response(entry, lang),
            'confidence': round(float(confidence), 3),
            'kb_entry_id': entry['id'],
            'category': entry['category'],
            'ticket_category': entry.get('ticket_category'),
            'category_slug': entry.get('category_slug'),
            'can_escalate': True,
        }

    def _direct_match(self, question: str, lang: str) -> Optional[Dict]:
        normalized_question = self._normalize_text(question)
        if not normalized_question:
            return None

        best_entry = None
        best_score = 0.0
        for entry in self.knowledge_base:
            score = 0.0
            for term in entry.get('keywords_en', []) + entry.get('keywords_es', []):
                normalized_term = self._normalize_text(term)
                if normalized_term and normalized_term in normalized_question:
                    score += 1.4 if (' ' in normalized_term or len(normalized_term) >= 8) else 1.0

            if score > best_score:
                best_entry = entry
                best_score = score

        if best_entry and best_score >= 1.0:
            confidence = min(0.99, 0.55 + (best_score * 0.08))
            return self._build_answer(best_entry, lang, confidence)

        return None
    
    def find_answer(self, question: str, lang: str = 'es') -> Optional[Dict]:
        """Find best matching answer for user question.
        
        Args:
            question: User's question or problem description
            
        Returns:
            Dict with keys:
                - answer: str with the response
                - confidence: float 0-1
                - kb_entry_id: int
                - category: str
                - can_escalate: bool (suggest escalation?)
            Or None if no good match found
        """
        if not question or not self.vectorizer or self.tfidf_matrix is None:
            return None
        
        try:
            direct_answer = self._direct_match(question, lang)
            if direct_answer is not None:
                return direct_answer

            # Vectorize the question
            q_vector = self.vectorizer.transform([question.lower()])
            
            # Calculate similarity to all KB entries
            similarities = cosine_similarity(q_vector, self.tfidf_matrix)[0]
            
            # Find best match
            best_idx = np.argmax(similarities)
            best_score = similarities[best_idx]
            
            kb_entry = self.knowledge_base[best_idx]
            min_confidence = kb_entry.get('confidence_min', 0.65)
            
            # Only return if confidence is high enough
            if best_score >= min_confidence:
                return self._build_answer(kb_entry, lang, best_score)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error finding answer: {e}")
            return None
    
    def get_all_categories(self) -> List[str]:
        """Get list of all categories in knowledge base."""
        return sorted(list(set(entry['category'] for entry in self.knowledge_base)))
    
    def get_entries_by_category(self, category: str) -> List[Dict]:
        """Get all KB entries for a category."""
        return [e for e in self.knowledge_base if e['category'] == category]


# Global chatbot instance
_chatbot = None


def get_chatbot() -> ChatBot:
    """Get or create chatbot instance."""
    global _chatbot
    if _chatbot is None:
        _chatbot = ChatBot()
    return _chatbot


def _call_llm_api(messages: List[Dict], lang: str = 'es') -> Optional[str]:
    """Call an LLM API (Groq or OpenAI) for intelligent responses."""
    import os
    import requests
    
    # Try Groq first (free tier with generous limits)
    groq_api_key = (os.environ.get('GROQ_API_KEY') or '').strip()
    if groq_api_key:
        groq_models = [
            'llama-3.3-70b-versatile',
            'llama-3.1-8b-instant',
            'mixtral-8x7b-32768',
        ]
        for model in groq_models:
            try:
                response = requests.post(
                    'https://api.groq.com/openai/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {groq_api_key}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'model': model,
                        'messages': messages,
                        'max_tokens': 500,
                        'temperature': 0.7,
                    },
                    timeout=20,
                )
                if response.status_code == 200:
                    content = response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
                    if content and content.strip():
                        return content.strip()
                else:
                    logger.warning('Groq API non-200 (model=%s, status=%s, body=%s)', model, response.status_code, response.text[:280])
            except Exception as e:
                logger.warning('Groq API error (model=%s): %s', model, e)
    else:
        logger.warning('GROQ_API_KEY is not configured or is empty.')
    
    # Try OpenAI as fallback
    openai_api_key = (os.environ.get('OPENAI_API_KEY') or '').strip()
    if openai_api_key:
        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {openai_api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'gpt-4o-mini',
                    'messages': messages,
                    'max_tokens': 500,
                    'temperature': 0.7,
                },
                timeout=20,
            )
            if response.status_code == 200:
                content = response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
                if content and content.strip():
                    return content.strip()
            else:
                logger.warning('OpenAI API non-200 (status=%s, body=%s)', response.status_code, response.text[:280])
        except Exception as e:
            logger.warning(f'OpenAI API error: {e}')
    
    return None


def converse_with_assistant(user_id: int, user_message: str, lang: str = 'es') -> Dict:
    """Have an intelligent conversation with the assistant using LLM if available.
    
    Falls back to knowledge base if no LLM is configured.
    
    Args:
        user_id: User ID for conversation history
        user_message: User's message
        lang: Language ('en' or 'es')
    
    Returns:
        Dict with reply, used_llm flag, and confidence
    """
    conversation = get_conversation_history(user_id)
    add_to_conversation(user_id, 'user', user_message)
    
    # Build messages for LLM
    system_prompt = _build_system_prompt(lang)
    messages = [{'role': 'system', 'content': system_prompt}]
    
    # Add conversation history (last 10 messages for context)
    for msg in conversation[-10:]:
        messages.append({
            'role': msg['role'],
            'content': msg['content'],
        })
    
    # Add current user message
    messages.append({'role': 'user', 'content': user_message})
    
    # Try LLM first
    llm_response = _call_llm_api(messages, lang)
    
    if llm_response:
        add_to_conversation(user_id, 'assistant', llm_response)
        return {
            'reply': llm_response,
            'used_llm': True,
            'confidence': 0.9,
        }
    
    # Fallback to knowledge base
    kb_answer = answer_question(user_message, lang=lang)
    
    if kb_answer:
        add_to_conversation(user_id, 'assistant', kb_answer['answer'])
        return {
            'reply': kb_answer['answer'],
            'used_llm': False,
            'confidence': kb_answer['confidence'],
            'ticket_category': kb_answer.get('ticket_category'),
        }
    
    # Default fallback response
    if lang == 'es':
        default_reply = "No estoy seguro cómo ayudarte con eso. ¿Puedes describir el problema con más detalle? O crea un ticket y un técnico te ayudará."
    else:
        default_reply = "I'm not sure how to help with that. Can you describe the issue in more detail? Or create a support ticket and a technician will assist you."
    
    add_to_conversation(user_id, 'assistant', default_reply)
    return {
        'reply': default_reply,
        'used_llm': False,
        'confidence': 0.0,
    }


def answer_question(question: str, lang: str = 'es') -> Optional[Dict]:
    """Find automatic answer for a question.
    
    Args:
        question: User question or ticket description
        
    Returns:
        Answer dict or None
    """
    chatbot = get_chatbot()
    return chatbot.find_answer(question, lang=lang)


def should_auto_respond(title: str, description: str = "", confidence_threshold: float = 0.75) -> bool:
    """Determine if ticket should get automatic response.
    
    Args:
        title: Ticket title
        description: Ticket description
        confidence_threshold: Min confidence to auto-respond (0-1)
        
    Returns:
        True if should auto-respond
    """
    chatbot = get_chatbot()
    full_text = f"{title} {description}".strip()
    answer = chatbot.find_answer(full_text)
    
    if answer is None:
        return False
    
    return answer['confidence'] >= confidence_threshold
