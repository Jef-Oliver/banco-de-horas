from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ValidationError
from datetime import datetime, date, timedelta

class Departamento(models.Model):
    nome = models.CharField(max_length=255)
    sigla = models.CharField(max_length=20, unique=True)

    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.sigla})"

class Perfil(models.Model):
    TIPOS = [
        ('ADM', 'Administrador'),
        ('GESTOR', 'Gestor'),
        ('SERVIDOR', 'Servidor'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    tipo = models.CharField(max_length=10, choices=TIPOS)
    departamento = models.ForeignKey(Departamento, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Perfil de Usuário"
        verbose_name_plural = "Perfis de Usuário"

    def __str__(self):
        return f"{self.user.username} - {self.get_tipo_display()}"

class Servidor(models.Model):
    CARGA_CHOICES = [
        (4, '4 horas'),
        (6, '6 horas'),
        (8, '8 horas'),
        (12, '12 horas'),
    ]
    
    nome_completo = models.CharField(max_length=255)
    cpf = models.CharField(max_length=14, unique=True, verbose_name="CPF")
    carga_horaria_diaria = models.IntegerField(choices=CARGA_CHOICES, verbose_name="Carga Horária Diária")
    departamento = models.ForeignKey(Departamento, on_delete=models.PROTECT, related_name='servidores')
    usuario = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='servidor_perfil')
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Servidor"
        verbose_name_plural = "Servidores"
        ordering = ['nome_completo']

    def __str__(self):
        return self.nome_completo

class RegistroPonto(models.Model):
    servidor = models.ForeignKey(Servidor, on_delete=models.CASCADE, related_name='pontos')
    data = models.DateField()
    entrada = models.TimeField()
    saida = models.TimeField()
    minutos_trabalhados = models.IntegerField(editable=False, default=0)
    saldo_minutos_dia = models.IntegerField(editable=False, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro de Ponto"
        verbose_name_plural = "Registros de Ponto"
        unique_together = ('servidor', 'data')
        ordering = ['-data']

    def clean(self):
        if self.saida <= self.entrada:
            raise ValidationError({'saida': "O horário de saída deve ser maior que o de entrada."})

    def save(self, *args, **kwargs):
        # Calcular minutos trabalhados
        d1 = datetime.combine(date.today(), self.entrada)
        d2 = datetime.combine(date.today(), self.saida)
        diff = d2 - d1
        self.minutos_trabalhados = int(diff.total_seconds() / 60)
        
        # Calcular saldo do dia: apenas horas excedentes acumulam
        # Se trabalhar menos que a carga, o saldo do banco de horas é zero (não abate)
        carga_minutos = self.servidor.carga_horaria_diaria * 60
        saldo = self.minutos_trabalhados - carga_minutos
        self.saldo_minutos_dia = max(0, saldo)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.servidor.nome_completo} - {self.data}"

class Compensacao(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('APROVADO', 'Aprovado'),
        ('REJEITADO', 'Rejeitado'),
    ]
    
    servidor = models.ForeignKey(Servidor, on_delete=models.CASCADE, related_name='compensacoes')
    data = models.DateField(verbose_name="Data da Folga/Compensação")
    minutos_descontados = models.IntegerField(verbose_name="Minutos a Descontar")
    descricao = models.CharField(max_length=255, blank=True, verbose_name="Descrição/Motivo")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='APROVADO', verbose_name="Status")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Compensação/Folga"
        verbose_name_plural = "Compensações/Folgas"
        ordering = ['-data']

    def __str__(self):
        return f"Compensação: {self.servidor.nome_completo} - {self.data}"
