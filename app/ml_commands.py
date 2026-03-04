"""
Comandos CLI para el sistema de Machine Learning
"""

import click
from flask import Flask
from app import db


def register_ml_commands(app: Flask):
    """Registra comandos ML en la aplicación Flask"""
    
    @app.cli.command('ml-train')
    @click.option('--min-tickets', default=10, help='Mínimo de tickets para entrenar')
    def train_model(min_tickets):
        """Entrena el modelo de clasificación de tickets"""
        try:
            from app.ml_classifier import classifier, ML_AVAILABLE
            
            if not ML_AVAILABLE:
                click.echo("❌ ML dependencies not available. Install them with:")
                click.echo("   pip install scikit-learn numpy")
                return
            
            click.echo('Iniciando entrenamiento del modelo ML...')
            
            result = classifier.train(min_tickets=min_tickets)
            
            if result['success']:
                click.echo(f"✅ Modelo entrenado exitosamente!")
                click.echo(f"   Precisión: {result['accuracy']:.2%}")
                click.echo(f"   Total de tickets: {result['total_tickets']}")
                click.echo(f"   Tickets de entrenamiento: {result['train_size']}")
                click.echo(f"   Tickets de prueba: {result['test_size']}")
                click.echo(f"   Número de técnicos: {result['num_technicians']}")
            else:
                click.echo(f"❌ Error: {result['error']}")
        except Exception as e:
            click.echo(f"❌ Error: {e}")
    
    @app.cli.command('ml-info')
    def model_info():
        """Muestra información del modelo actual"""
        try:
            from app.ml_classifier import classifier, ML_AVAILABLE
            
            if not ML_AVAILABLE:
                click.echo("❌ ML dependencies not available. Install them with:")
                click.echo("   pip install scikit-learn numpy")
                return
            
            info = classifier.get_model_info()
            
            if info['trained']:
                click.echo("📊 Información del Modelo ML:")
                click.echo(f"   Estado: Entrenado ✅")
                if info.get('trained_at'):
                    click.echo(f"   Fecha de entrenamiento: {info['trained_at']}")
                click.echo(f"   Número de técnicos: {info.get('num_technicians', 'N/A')}")
                click.echo(f"   Características de texto: {info.get('num_features', 'N/A')}")
            else:
                click.echo("⚠️  Modelo no entrenado. Ejecuta 'flask ml-train' primero.")
        except Exception as e:
            click.echo(f"❌ Error: {e}")
    
    @app.cli.command('ml-stats')
    def technician_stats():
        """Muestra estadísticas de técnicos"""
        try:
            from app.ml_classifier import ML_AVAILABLE
            from app.models import TechnicianStats
            
            if not ML_AVAILABLE:
                click.echo("❌ ML dependencies not available. Install them with:")
                click.echo("   pip install scikit-learn numpy")
                return
            
            stats = TechnicianStats.query.all()
            
            if not stats:
                click.echo("No hay estadísticas disponibles.")
                return
            
            click.echo("\n👥 Estadísticas de Técnicos:\n")
            
            for stat in stats:
                tech = stat.technician
                click.echo(f"🔧 {tech.username} ({tech.email})")
                click.echo(f"   Tickets resueltos: {stat.total_tickets_resolved}")
                
                if stat.avg_resolution_time:
                    hours = stat.avg_resolution_time / 60
                    click.echo(f"   Tiempo promedio: {hours:.1f} horas")
                
                if stat.avg_satisfaction:
                    click.echo(f"   Satisfacción promedia: {stat.avg_satisfaction:.1f}/5.0 ⭐")
                
                if stat.specialization:
                    import json
                    specs = json.loads(stat.specialization)
                    top_category = max(specs.items(), key=lambda x: x[1])[0] if specs else 'N/A'
                    click.echo(f"   Especialización: {top_category}")
                
                click.echo()

