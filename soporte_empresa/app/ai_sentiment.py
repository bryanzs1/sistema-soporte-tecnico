"""AI-powered sentiment analysis for support tickets.

Analyzes ticket descriptions to detect customer sentiment and urgency.
"""

import os
import logging
from typing import Dict, Tuple

from soporte_empresa.app import db
# Try to import sentiment analysis tools
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

logger = logging.getLogger(__name__)

# Sentiment thresholds
SENTIMENT_THRESHOLDS = {
    'very_negative': -0.7,      # Very angry/frustrated
    'negative': -0.3,            # Frustrated
    'neutral': 0.3,              # Balanced
    'positive': 0.7,             # Satisfied
}

# Urgency keywords that increase priority
URGENCY_KEYWORDS = {
    'critical': ['critical', 'emergency', 'urgent', 'asap', 'immediately', 'down', 'broken', 'not working'],
    'high': ['need', 'help', 'problem', 'error', 'fail', 'crash', 'stuck', 'cannot', 'blocked'],
    'medium': ['issue', 'question', 'slow', 'difficult'],
}


class SentimentAnalyzer:
    """Analyze sentiment and urgency in ticket descriptions."""
    
    def __init__(self):
        """Initialize sentiment analyzer."""
        self.available = TEXTBLOB_AVAILABLE
        if not self.available:
            logger.warning("TextBlob not available. Sentiment analysis will use keyword matching only.")
    
    def analyze(self, text: str) -> Dict:
        """Analyze sentiment and urgency of ticket text.
        
        Args:
            text: Ticket description or title
            
        Returns:
            Dict with keys:
                - sentiment_score: float between -1 and 1
                - sentiment_label: 'very_negative', 'negative', 'neutral', 'positive'
                - urgency_level: 'high', 'medium', 'low'
                - confidence: float 0-1
                - explanation: str describing the analysis
        """
        if not text or not isinstance(text, str):
            return self._default_result()
        
        text_lower = text.lower()
        
        # Get sentiment score
        if self.available:
            sentiment_score = self._get_textblob_sentiment(text)
        else:
            sentiment_score = self._get_keyword_sentiment(text_lower)
        
        # Determine sentiment label
        sentiment_label = self._label_sentiment(sentiment_score)
        
        # Analyze urgency keywords
        urgency_level, urgency_score = self._analyze_urgency(text_lower)
        
        # Calculate confidence based on text length and keyword matches
        confidence = min(0.95, 0.5 + len(text) / 1000)
        
        # Build explanation
        explanation = self._build_explanation(sentiment_label, urgency_level, text_lower)
        
        return {
            'sentiment_score': round(sentiment_score, 3),
            'sentiment_label': sentiment_label,
            'urgency_level': urgency_level,
            'urgency_score': round(urgency_score, 3),
            'confidence': round(confidence, 3),
            'explanation': explanation,
        }
    
    def _get_textblob_sentiment(self, text: str) -> float:
        """Get sentiment using TextBlob polarity."""
        try:
            blob = TextBlob(text)
            # polarity is -1 to 1, subjectivity is 0 to 1
            polarity = blob.sentiment.polarity
            
            # Adjust based on subjectivity (more subjective = more confident opinion)
            subjectivity = blob.sentiment.subjectivity
            adjusted_polarity = polarity * (0.5 + subjectivity * 0.5)
            
            return adjusted_polarity
        except Exception as e:
            logger.warning(f"Error in TextBlob sentiment: {e}")
            return self._get_keyword_sentiment(text.lower())
    
    def _get_keyword_sentiment(self, text_lower: str) -> float:
        """Fallback sentiment analysis using keywords."""
        score = 0.0
        
        # Positive keywords
        positive = ['solved', 'working', 'thanks', 'appreciate', 'great', 'excellent', 'perfect', 'good']
        for word in positive:
            score += text_lower.count(word) * 0.2
        
        # Negative keywords
        negative = ['broken', 'error', 'fail', 'crash', 'problem', 'issue', 'bad', 'terrible', 'hate', 'angry']
        for word in negative:
            score -= text_lower.count(word) * 0.3
        
        # Normalize to -1 to 1
        return max(-1.0, min(1.0, score))
    
    def _label_sentiment(self, score: float) -> str:
        """Convert sentiment score to label."""
        if score <= SENTIMENT_THRESHOLDS['very_negative']:
            return 'very_negative'
        elif score <= SENTIMENT_THRESHOLDS['negative']:
            return 'negative'
        elif score <= SENTIMENT_THRESHOLDS['neutral']:
            return 'neutral'
        elif score <= SENTIMENT_THRESHOLDS['positive']:
            return 'positive'
        else:
            return 'very_positive'
    
    def _analyze_urgency(self, text_lower: str) -> Tuple[str, float]:
        """Analyze urgency based on keywords."""
        urgency_score = 0.0
        
        # Check for critical keywords
        for keyword in URGENCY_KEYWORDS['critical']:
            urgency_score += text_lower.count(keyword) * 0.4
        
        # Check for high priority keywords
        for keyword in URGENCY_KEYWORDS['high']:
            urgency_score += text_lower.count(keyword) * 0.2
        
        # Check for medium priority keywords
        for keyword in URGENCY_KEYWORDS['medium']:
            urgency_score += text_lower.count(keyword) * 0.1
        
        # Normalize
        urgency_score = min(1.0, urgency_score)
        
        # Determine level
        if urgency_score >= 0.7:
            level = 'high'
        elif urgency_score >= 0.3:
            level = 'medium'
        else:
            level = 'low'
        
        return level, urgency_score
    
    def _build_explanation(self, sentiment: str, urgency: str, text_lower: str) -> str:
        """Build human-readable explanation."""
        parts = []
        
        # Sentiment explanation
        if sentiment == 'very_negative':
            parts.append("Very angry/frustrated customer")
        elif sentiment == 'negative':
            parts.append("Customer seems frustrated")
        elif sentiment == 'neutral':
            parts.append("Neutral tone")
        elif sentiment == 'positive':
            parts.append("Customer in good mood")
        else:
            parts.append("Very satisfied customer")
        
        # Urgency explanation
        if urgency == 'high':
            parts.append("High urgency indicators found")
        elif urgency == 'medium':
            parts.append("Some urgency indicators")
        
        return " - ".join(parts)
    
    def _default_result(self) -> Dict:
        """Return default neutral result for empty text."""
        return {
            'sentiment_score': 0.0,
            'sentiment_label': 'neutral',
            'urgency_level': 'medium',
            'urgency_score': 0.5,
            'confidence': 0.0,
            'explanation': 'No text provided',
        }
    
    def get_priority_adjustment(self, sentiment_label: str) -> int:
        """Get priority level adjustment based on sentiment.
        
        Args:
            sentiment_label: Output from analyze()
            
        Returns:
            Priority adjustment (-2 to +2)
        """
        adjustments = {
            'very_negative': 2,    # Bump up significantly
            'negative': 1,          # Bump up slightly
            'neutral': 0,           # No change
            'positive': -1,         # Lower slightly
            'very_positive': 0,     # Keep same
        }
        return adjustments.get(sentiment_label, 0)
    
    def get_urgency_adjustment(self, urgency_level: str) -> int:
        """Get priority level adjustment based on urgency.
        
        Args:
            urgency_level: 'high', 'medium', or 'low'
            
        Returns:
            Priority adjustment
        """
        adjustments = {
            'high': 2,
            'medium': 0,
            'low': -1,
        }
        return adjustments.get(urgency_level, 0)


# Global analyzer instance
_analyzer = None


def get_analyzer() -> SentimentAnalyzer:
    """Get or create sentiment analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = SentimentAnalyzer()
    return _analyzer


def analyze_ticket(title: str, description: str = "") -> Dict:
    """Analyze sentiment of a ticket.
    
    Args:
        title: Ticket title
        description: Ticket description
        
    Returns:
        Analysis result dict
    """
    analyzer = get_analyzer()
    
    # Combine title and description for analysis
    full_text = f"{title} {description}".strip()
    
    return analyzer.analyze(full_text)
