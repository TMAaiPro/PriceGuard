from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Creates TimescaleDB hypertables for time-series data models'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Check if TimescaleDB extension is installed
            cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'timescaledb');")
            extension_exists = cursor.fetchone()[0]
            
            if not extension_exists:
                self.stdout.write(self.style.ERROR('TimescaleDB extension is not installed'))
                self.stdout.write(self.style.WARNING('Run CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE; in your PostgreSQL database'))
                return
            
            # Create hypertables for models that store time-series data
            self.stdout.write(self.style.NOTICE('Creating hypertables for time-series data...'))
            
            # Example: Convert product_price table to hypertable
            try:
                cursor.execute("""
                SELECT create_hypertable('products_productprice', 'timestamp', 
                                       if_not_exists => TRUE,
                                       create_default_indexes => TRUE);
                """)
                self.stdout.write(self.style.SUCCESS('Created hypertable for products_productprice'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating hypertable for products_productprice: {e}'))
            
            # Add more hypertables as needed
            
            self.stdout.write(self.style.SUCCESS('Hypertable creation completed'))
