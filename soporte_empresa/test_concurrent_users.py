"""
Test concurrent database operations at the application level.
Simulates multiple users performing operations simultaneously.
"""
import pytest
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from app import create_app, db
from app.models import User, Ticket, TicketOption


def _skip_if_sqlite(app):
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if db_uri.startswith('sqlite'):
        pytest.skip('Concurrent write stress tests are unreliable on SQLite; run with PostgreSQL for representative results.')


@pytest.fixture
def app():
    """Create application with in-memory SQLite for testing."""
    app = create_app('config.TestingConfig')
    
    with app.app_context():
        db.create_all()
        
        # Create test users
        for i in range(5):
            user = User(username=f'user{i}', email=f'user{i}@test.com', role='user')
            user.set_password('password123')
            db.session.add(user)
        
        # Create ticket options
        for cat in ['Red', 'Impresoras', 'Software', 'Hardware']:
            opt = TicketOption(option_type='category', value=cat, active=True)
            db.session.add(opt)
        
        for pri in ['Baja', 'Media', 'Alta', 'Crítica']:
            opt = TicketOption(option_type='priority', value=pri, active=True)
            db.session.add(opt)
        
        db.session.commit()
        
    yield app
    
    with app.app_context():
        db.session.remove()
        db.drop_all()


class TestConcurrentUsers:
    """Test suite for concurrent user access."""
    
    def test_concurrent_user_creation(self, app):
        """Test creating multiple users simultaneously without conflicts."""
        _skip_if_sqlite(app)
        users_created = []
        errors = []
        
        def create_user(user_num):
            """Create a user in the thread context."""
            try:
                with app.app_context():
                    user = User(
                        username=f'concurrent_user_{user_num}',
                        email=f'concurrent_{user_num}@test.com',
                        role='user'
                    )
                    user.set_password('password')
                    db.session.add(user)
                    db.session.commit()
                    users_created.append(user.id)
            except Exception as e:
                errors.append(str(e))
        
        # Create users in parallel threads
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_user, i) for i in range(5)]
            for future in as_completed(futures):
                future.result()
        
        assert not errors, f"Errors during concurrent user creation: {errors}"
        assert len(users_created) == 5, f"Created {len(users_created)} users, expected 5"
        
        # Verify all users exist in database
        with app.app_context():
            count = User.query.filter(
                User.username.like('concurrent_user_%')
            ).count()
            assert count == 5, f"Database has {count} concurrent users, expected 5"
    
    def test_concurrent_ticket_creation(self, app):
        """Test creating tickets concurrently without data corruption."""
        _skip_if_sqlite(app)
        tickets_created = []
        errors = []
        
        def create_ticket(ticket_num):
            """Create a ticket in the thread context."""
            try:
                with app.app_context():
                    ticket = Ticket(
                        title=f'Concurrent Ticket {ticket_num}',
                        description=f'Test ticket {ticket_num}',
                        creator_name=f'User {ticket_num}',
                        category='Red',
                        priority='Media',
                        status='Abierto'
                    )
                    db.session.add(ticket)
                    db.session.commit()
                    tickets_created.append(ticket.id)
            except Exception as e:
                errors.append(str(e))
        
        # Create tickets in parallel
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_ticket, i) for i in range(10)]
            for future in as_completed(futures):
                future.result()
        
        assert not errors, f"Errors creating tickets: {errors}"
        assert len(tickets_created) == 10, f"Created {len(tickets_created)} tickets, expected 10"
        
        # Verify all tickets exist and are valid
        with app.app_context():
            tickets = Ticket.query.all()
            assert len(tickets) == 10, f"Database has {len(tickets)} tickets, expected 10"
            
            # Check data integrity
            for ticket in tickets:
                assert ticket.title.startswith('Concurrent Ticket'), "Title corrupted"
                assert ticket.status == 'Abierto', f"Status invalid: {ticket.status}"
                assert len(ticket.creator_name) > 0, "Creator name missing"
    
    def test_concurrent_ticket_updates(self, app):
        """Test updating the same ticket from multiple threads simultaneously."""
        _skip_if_sqlite(app)
        # Create a ticket
        with app.app_context():
            ticket = Ticket(
                title='Update Test Ticket',
                description='Original description',
                creator_name='TestUser',
                category='Red',
                priority='Media',
                status='Abierto'
            )
            db.session.add(ticket)
            db.session.commit()
            ticket_id = ticket.id
        
        # Track updates
        successful_updates = []
        errors = []
        
        def update_ticket(update_num):
            """Update the same ticket from concurrent threads."""
            try:
                with app.app_context():
                    ticket = Ticket.query.get(ticket_id)
                    if ticket:
                        # Simulate some work
                        new_status = ['En proceso', 'Esperando usuario', 'Cerrado'][update_num % 3]
                        ticket.status = new_status
                        ticket.description = f'Updated by thread {update_num}'
                        db.session.commit()
                        successful_updates.append(update_num)
            except Exception as e:
                errors.append(str(e))
        
        # Update from multiple threads simultaneously
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(update_ticket, i) for i in range(8)]
            for future in as_completed(futures):
                future.result()
        
        assert not errors, f"Errors updating ticket: {errors}"
        assert len(successful_updates) == 8, f"Successful updates: {len(successful_updates)}, expected 8"
        
        # Verify final state is valid
        with app.app_context():
            final_ticket = Ticket.query.get(ticket_id)
            assert final_ticket is not None, "Ticket was deleted"
            assert final_ticket.status in ['Abierto', 'En proceso', 'Esperando usuario', 'Cerrado'], \
                f"Invalid final status: {final_ticket.status}"
            assert len(final_ticket.description) > 0, "Description was corrupted"
    
    def test_concurrent_read_operations(self, app):
        """Test multiple threads reading data simultaneously."""
        _skip_if_sqlite(app)
        # Create sample data
        with app.app_context():
            for i in range(20):
                ticket = Ticket(
                    title=f'Read Test Ticket {i}',
                    description=f'Test {i}',
                    creator_name='Reader',
                    category='Red',
                    priority='Media',
                    status='Abierto'
                )
                db.session.add(ticket)
            db.session.commit()
        
        read_results = []
        errors = []
        
        def read_tickets(reader_num):
            """Read all tickets from concurrent thread."""
            try:
                with app.app_context():
                    tickets = Ticket.query.all()
                    assert len(tickets) == 20, f"Found {len(tickets)} tickets, expected 20"
                    read_results.append(len(tickets))
            except Exception as e:
                errors.append(str(e))
        
        # Concurrent reads
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(read_tickets, i) for i in range(10)]
            for future in as_completed(futures):
                future.result()
        
        assert not errors, f"Errors during reads: {errors}"
        assert len(read_results) == 10, f"Completed {len(read_results)} reads, expected 10"
        assert all(count == 20 for count in read_results), "Data inconsistency during reads"
    
    def test_concurrent_mixed_operations(self, app):
        """Test mixed read/write operations from multiple threads."""
        _skip_if_sqlite(app)
        created_ids = []
        read_counts = []
        update_counts = []
        errors = []
        lock = threading.Lock()
        
        def create_tickets(creator_id):
            """Create 3 tickets per thread."""
            try:
                with app.app_context():
                    for i in range(3):
                        ticket = Ticket(
                            title=f'Mixed Op Ticket - Creator {creator_id} - {i}',
                            description=f'Mixed operation test',
                            creator_name=f'Creator {creator_id}',
                            category='Red',
                            priority='Media',
                            status='Abierto'
                        )
                        db.session.add(ticket)
                        db.session.commit()
                        with lock:
                            created_ids.append(ticket.id)
            except Exception as e:
                errors.append(('create', str(e)))
        
        def read_tickets():
            """Read all tickets."""
            try:
                with app.app_context():
                    count = Ticket.query.count()
                    with lock:
                        read_counts.append(count)
            except Exception as e:
                errors.append(('read', str(e)))
        
        def update_tickets():
            """Update tickets."""
            try:
                with app.app_context():
                    tickets = Ticket.query.limit(5).all()
                    for ticket in tickets:
                        ticket.status = 'En proceso'
                        db.session.commit()
                    with lock:
                        update_counts.append(len(tickets))
            except Exception as e:
                errors.append(('update', str(e)))
        
        # Run mixed operations in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 3 creators, 4 readers, 3 updaters
            futures = []
            for i in range(3):
                futures.append(executor.submit(create_tickets, i))
            for i in range(4):
                futures.append(executor.submit(read_tickets))
            for i in range(3):
                futures.append(executor.submit(update_tickets))
            
            for future in as_completed(futures):
                future.result()
        
        assert not errors, f"Errors during mixed operations: {errors}"
        assert len(created_ids) == 9, f"Created {len(created_ids)} tickets, expected 9"
        assert len(read_counts) > 0, "No read operations completed"
        assert len(update_counts) > 0, "No update operations completed"
        
        # Verify final state
        with app.app_context():
            final_count = Ticket.query.count()
            assert final_count == 9, f"Final ticket count is {final_count}, expected 9"
    
    def test_database_connection_pool_isolation(self, app):
        """Test that each thread gets its own database session/connection."""
        thread_operations = []
        errors = []
        lock = threading.Lock()
        
        def thread_operation(thread_num):
            """Perform DB operation from thread."""
            try:
                with app.app_context():
                    # Each thread context gets its own session
                    user_count = User.query.count()
                    ticket_count = Ticket.query.count()
                    with lock:
                        thread_operations.append((thread_num, user_count, ticket_count))
            except Exception as e:
                errors.append(str(e))
        
        # Multiple threads accessing database
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(thread_operation, i) for i in range(8)]
            for future in as_completed(futures):
                future.result()
        
        assert not errors, f"Errors accessing database: {errors}"
        # All threads should see consistent data
        assert len(thread_operations) == 8, f"Only {len(thread_operations)} threads completed"
        # All should see the same user count (6 from fixture + initial ones)
        user_counts = [op[1] for op in thread_operations]
        assert len(set(user_counts)) == 1, f"Inconsistent user counts: {user_counts}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
