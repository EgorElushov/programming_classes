# Generated by Django 5.1.7 on 2025-04-18 22:53

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('competition', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Problem',
            fields=[
                ('problem_id', models.AutoField(primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('difficulty', models.CharField(max_length=50)),
                (
                    'competition',
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='competition.competition'),
                ),
            ],
        ),
    ]
