"""
Sistema de Clasificación Inteligente de Tickets con Machine Learning
Asigna automáticamente tickets a técnicos basándose en:
- Contenido del ticket (título + descripción)
- Categoría y prioridad
- Experiencia y rendimiento histórico del técnico
"""

import pickle
import os
import json
from datetime import datetime, timedelta

# Lazy imports for ML dependencies - will be imported only when needed
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import LabelEncoder
    from sklearn.metrics import accuracy_score, classification_report
    ML_AVAILABLE = True
except ImportError as e:
    ML_AVAILABLE = False
    _ml_import_error = str(e)

from app import db
from app.models import Ticket, User, TechnicianStats


class TicketClassifier:
    """Clasificador inteligente de tickets usando Random Forest"""
    
    def __init__(self):
        self.model = None
        self.vectorizer = None
        self.category_encoder = None
        self.priority_encoder = None
        self.technician_encoder = None
        self.is_trained = False
        self.model_path = 'ml_models'
        
        # Crear directorio para modelos si no existe
        if not os.path.exists(self.model_path):
            os.makedirs(self.model_path)
    
    def _prepare_features(self, tickets_data):
        """Prepara características para el modelo"""
        # Combinar título y descripción para análisis de texto
        texts = [f"{t['title']} {t['description']}" for t in tickets_data]
        
        # Vectorizar texto con TF-IDF
        if self.vectorizer is None:
            self.vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words=None,  # Podríamos agregar stop words en español
                ngram_range=(1, 2)
            )
            text_features = self.vectorizer.fit_transform(texts)
        else:
            text_features = self.vectorizer.transform(texts)
        
        # Codificar categorías
        categories = [t['category'] for t in tickets_data]
        if self.category_encoder is None:
            self.category_encoder = LabelEncoder()
            category_features = self.category_encoder.fit_transform(categories)
        else:
            category_features = self.category_encoder.transform(categories)
        
        # Codificar prioridades
        priorities = [t['priority'] for t in tickets_data]
        if self.priority_encoder is None:
            self.priority_encoder = LabelEncoder()
            priority_features = self.priority_encoder.fit_transform(priorities)
        else:
            priority_features = self.priority_encoder.transform(priorities)
        
        # Combinar todas las características
        text_array = text_features.toarray()
        category_array = category_features.reshape(-1, 1)
        priority_array = priority_features.reshape(-1, 1)
        
        features = np.hstack([text_array, category_array, priority_array])
        
        return features
    
    def train(self, min_tickets=10):
        """
        Entrena el modelo con datos históricos
        
        Args:
            min_tickets: Número mínimo de tickets para entrenar
            
        Returns:
            dict: Métricas del entrenamiento
        """
        if not ML_AVAILABLE:
            return {
                'success': False,
                'error': f'Machine Learning dependencies not available. Please install scikit-learn: pip install scikit-learn numpy'
            }
        
        # Obtener tickets cerrados con técnico asignado
        tickets = Ticket.query.filter(
            Ticket.status == 'Cerrado',
            Ticket.technician_id.isnot(None),
            Ticket.resolved_at.isnot(None)
        ).all()
        
        if len(tickets) < min_tickets:
            return {
                'success': False,
                'error': f'Necesitas al menos {min_tickets} tickets cerrados para entrenar el modelo. Actualmente tienes {len(tickets)}.'
            }
        
        # Preparar datos
        tickets_data = []
        technician_ids = []
        
        for ticket in tickets:
            # Calcular tiempo de resolución si no está guardado
            if ticket.resolution_time_minutes is None and ticket.resolved_at and ticket.created_at:
                resolution_time = (ticket.resolved_at - ticket.created_at).total_seconds() / 60
                ticket.resolution_time_minutes = int(resolution_time)
            
            tickets_data.append({
                'title': ticket.title or '',
                'description': ticket.description or '',
                'category': ticket.category or 'Otro',
                'priority': ticket.priority or 'Media'
            })
            technician_ids.append(ticket.technician_id)
        
        db.session.commit()
        
        # Preparar características
        X = self._prepare_features(tickets_data)
        
        # Codificar técnicos (target)
        if self.technician_encoder is None:
            self.technician_encoder = LabelEncoder()
        y = self.technician_encoder.fit_transform(technician_ids)
        
        # Dividir en train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Entrenar modelo Random Forest
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            class_weight='balanced'  # Balancear clases desiguales
        )
        
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        # Evaluar
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Calcular estadísticas de técnicos
        self._update_technician_stats()
        
        # Guardar modelo
        self.save_model()
        
        return {
            'success': True,
            'accuracy': accuracy,
            'total_tickets': len(tickets),
            'train_size': len(X_train),
            'test_size': len(X_test),
            'num_technicians': len(self.technician_encoder.classes_)
        }
    
    def predict(self, ticket_data, top_n=3):
        """
        Predice los mejores técnicos para un ticket
        
        Args:
            ticket_data: dict con title, description, category, priority
            top_n: número de técnicos a retornar
            
        Returns:
            list: [(technician_id, confidence_score), ...]
        """
        if not ML_AVAILABLE:
            # Si ML no está disponible, retornar lista vacía (no auto-asignar)
            return []
        
        if not self.is_trained or self.model is None:
            # Intentar cargar modelo guardado
            if not self.load_model():
                return []
        
        # Preparar características del nuevo ticket
        X = self._prepare_features([ticket_data])
        
        # Obtener probabilidades para cada técnico
        probabilities = self.model.predict_proba(X)[0]
        
        # Obtener técnicos activos
        active_technicians = User.query.filter_by(
            role='technician',
            is_active=True
        ).all()
        
        active_tech_ids = {tech.id for tech in active_technicians}
        
        # Filtrar solo técnicos activos y que estén en el modelo
        predictions = []
        for idx, prob in enumerate(probabilities):
            tech_id = int(self.technician_encoder.classes_[idx])
            
            # Solo incluir si está activo
            if tech_id in active_tech_ids:
                # Bonus por experiencia reciente
                tech_stats = TechnicianStats.query.filter_by(technician_id=tech_id).first()
                if tech_stats:
                    # Ajustar probabilidad según rendimiento
                    if tech_stats.avg_satisfaction:
                        prob *= (1 + (tech_stats.avg_satisfaction - 3) * 0.1)  # Bonus si rating > 3
                
                predictions.append((tech_id, float(prob)))
        
        # Ordenar por probabilidad y retornar top N
        predictions.sort(key=lambda x: x[1], reverse=True)
        
        return predictions[:top_n]
    
    def _update_technician_stats(self):
        """Actualiza estadísticas de todos los técnicos"""
        technicians = User.query.filter_by(role='technician').all()
        
        for tech in technicians:
            # Tickets cerrados por este técnico
            closed_tickets = Ticket.query.filter_by(
                technician_id=tech.id,
                status='Cerrado'
            ).all()
            
            if not closed_tickets:
                continue
            
            # Calcular estadísticas
            total = len(closed_tickets)
            
            resolution_times = [
                t.resolution_time_minutes for t in closed_tickets 
                if t.resolution_time_minutes is not None
            ]
            avg_resolution = sum(resolution_times) / len(resolution_times) if resolution_times else None
            
            ratings = [
                t.satisfaction_rating for t in closed_tickets 
                if t.satisfaction_rating is not None
            ]
            avg_rating = sum(ratings) / len(ratings) if ratings else None
            
            # Encontrar especialización (categorías más frecuentes)
            category_counts = {}
            for t in closed_tickets:
                if t.category:
                    category_counts[t.category] = category_counts.get(t.category, 0) + 1
            
            specialization = json.dumps(category_counts)
            
            # Actualizar o crear stats
            stats = TechnicianStats.query.filter_by(technician_id=tech.id).first()
            if stats is None:
                stats = TechnicianStats(technician_id=tech.id)
                db.session.add(stats)
            
            stats.total_tickets_resolved = total
            stats.avg_resolution_time = avg_resolution
            stats.avg_satisfaction = avg_rating
            stats.specialization = specialization
            stats.last_updated = datetime.utcnow()
        
        db.session.commit()
    
    def save_model(self):
        """Guarda el modelo entrenado"""
        if not self.is_trained:
            return False
        
        model_file = os.path.join(self.model_path, 'ticket_classifier.pkl')
        
        model_data = {
            'model': self.model,
            'vectorizer': self.vectorizer,
            'category_encoder': self.category_encoder,
            'priority_encoder': self.priority_encoder,
            'technician_encoder': self.technician_encoder,
            'trained_at': datetime.utcnow().isoformat()
        }
        
        with open(model_file, 'wb') as f:
            pickle.dump(model_data, f)
        
        return True
    
    def load_model(self):
        """Carga el modelo guardado"""
        model_file = os.path.join(self.model_path, 'ticket_classifier.pkl')
        
        if not os.path.exists(model_file):
            return False
        
        try:
            with open(model_file, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.vectorizer = model_data['vectorizer']
            self.category_encoder = model_data['category_encoder']
            self.priority_encoder = model_data['priority_encoder']
            self.technician_encoder = model_data['technician_encoder']
            self.is_trained = True
            
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False
    
    def get_model_info(self):
        """Obtiene información del modelo actual"""
        if not self.is_trained:
            if not self.load_model():
                return {'trained': False}
        
        model_file = os.path.join(self.model_path, 'ticket_classifier.pkl')
        
        try:
            with open(model_file, 'rb') as f:
                model_data = pickle.load(f)
            
            return {
                'trained': True,
                'trained_at': model_data.get('trained_at'),
                'num_technicians': len(self.technician_encoder.classes_) if self.technician_encoder else 0,
                'num_features': self.vectorizer.max_features if self.vectorizer else 0
            }
        except:
            return {'trained': self.is_trained}


# Instancia global del clasificador
classifier = TicketClassifier()
