# Generated by Django 4.2.9 on 2024-01-06 09:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('chatbot', '0003_alter_patient_age_alter_patient_alias_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chat',
            name='session',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='chatbot.session'),
        ),
    ]
