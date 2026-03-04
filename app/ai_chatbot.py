"""AI-powered chatbot for automatic responses to common issues.

Provides automatic answers to frequently asked questions and common problems.
"""

import os
import logging
from typing import Dict, Optional, List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

# Knowledge base of common issues and solutions
# Format: {
#   'keywords': ['search', 'term'],
#   'patterns': ['pattern to match'],
#   'response': 'automated response text',
#   'category': 'Hardware|Software|Network|Account|Other',
#   'confidence_min': 0.7  # min similarity to consider a match
# }

KNOWLEDGE_BASE = [
    {
        'id': 1,
        'keywords': ['password', 'login', 'access', 'forgot', 'reset', 'locked'],
        'category': 'Account',
        'response': """I can help you reset your password!

**Quick steps:**
1. Go to the login page
2. Click "Forgot password?"
3. Enter your email
4. Check your inbox for reset link
5. Create a new password

**Still having issues?** Reply to this ticket and a technician will help you within 30 minutes.""",
        'category_slug': 'account_access',
        'confidence_min': 0.6,
    },
    {
        'id': 2,
        'keywords': ['printer', 'printing', 'print', 'not printing', 'paper', 'toner'],
        'category': 'Hardware',
        'response': """Let me help with your printer issue!

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
        'category_slug': 'hardware_printer',
        'confidence_min': 0.7,
    },
    {
        'id': 3,
        'keywords': ['wifi', 'internet', 'network', 'connection', 'connected', 'not connecting'],
        'category': 'Network',
        'response': """I can help with your network connection!

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
        'category_slug': 'network_wifi',
        'confidence_min': 0.65,
    },
    {
        'id': 4,
        'keywords': ['slow', 'lag', 'frozen', 'sluggish', 'hang', 'performance'],
        'category': 'Software',
        'response': """Your device is running slowly? Let's speed it up!

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
        'category_slug': 'performance_slow',
        'confidence_min': 0.7,
    },
    {
        'id': 5,
        'keywords': ['software', 'install', 'download', 'app', 'program', 'license'],
        'category': 'Software',
        'response': """Need software installed or licensed?

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
        'category_slug': 'software_install',
        'confidence_min': 0.65,
    },
    {
        'id': 6,
        'keywords': ['email', 'outlook', 'gmail', 'send', 'receive', 'not receiving'],
        'category': 'Software',
        'response': """Having email trouble?

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
        'category_slug': 'email_issues',
        'confidence_min': 0.7,
    },
    {
        'id': 7,
        'keywords': ['vpn', 'remote', 'access', 'connection', 'cannot access'],
        'category': 'Network',
        'response': """Having trouble with VPN or remote access?

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
        'category_slug': 'vpn_remote',
        'confidence_min': 0.6,
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
            # Combine all keywords for each KB entry
            kb_texts = [' '.join(entry['keywords']) for entry in self.knowledge_base]
            
            if kb_texts:
                self.vectorizer = TfidfVectorizer(
                    lowercase=True,
                    stop_words='english',
                    analyzer='char',
                    ngram_range=(2, 3),
                    min_df=1
                )
                self.tfidf_matrix = self.vectorizer.fit_transform(kb_texts)
                logger.info(f"ChatBot trained on {len(self.knowledge_base)} knowledge base entries")
        except Exception as e:
            logger.warning(f"Error training ChatBot: {e}")
    
    def find_answer(self, question: str) -> Optional[Dict]:
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
                return {
                    'answer': kb_entry['response'],
                    'confidence': round(float(best_score), 3),
                    'kb_entry_id': kb_entry['id'],
                    'category': kb_entry['category'],
                    'category_slug': kb_entry.get('category_slug'),
                    'can_escalate': True,  # User can escalate if not satisfied
                }
            
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


def answer_question(question: str) -> Optional[Dict]:
    """Find automatic answer for a question.
    
    Args:
        question: User question or ticket description
        
    Returns:
        Answer dict or None
    """
    chatbot = get_chatbot()
    return chatbot.find_answer(question)


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
