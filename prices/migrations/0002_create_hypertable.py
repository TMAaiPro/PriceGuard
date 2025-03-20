from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('prices', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            "SELECT create_hypertable('price_history', 'time');",
            "SELECT 1;"
        ),
        migrations.RunSQL(
            "SELECT add_retention_policy('price_history', INTERVAL '2 years');",
            "SELECT 1;"
        ),
        migrations.RunSQL(
            """
            SELECT add_compression_policy('price_history', INTERVAL '7 days');
            """,
            "SELECT 1;"
        ),
    ]