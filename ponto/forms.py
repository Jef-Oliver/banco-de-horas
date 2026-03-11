from django import forms
from django.contrib.auth.models import User
from .models import Servidor, RegistroPonto, Compensacao, Departamento, Perfil
from django.db.models import Sum
from .utils import format_minutos_hhmm
import re

class DepartamentoForm(forms.ModelForm):
    class Meta:
        model = Departamento
        fields = ['nome', 'sigla']

class UsuarioBaseForm(forms.Form):
    username = forms.CharField(max_length=150, label="Nome de Usuário (Login)")
    password = forms.CharField(widget=forms.PasswordInput(), label="Senha")
    password_confirm = forms.CharField(widget=forms.PasswordInput(), label="Confirmar Senha")

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        username = cleaned_data.get("username")

        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("As senhas não conferem.")
        
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nome de usuário já está em uso.")
            
        return cleaned_data

class GestorForm(UsuarioBaseForm, forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['departamento']
        labels = {
            'departamento': 'Setor Responsável'
        }
    
    nome_completo = forms.CharField(max_length=255, label="Nome do Gestor")
    cpf = forms.CharField(max_length=14, label="CPF")

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        cpf = re.sub(r'[^0-9]', '', cpf)
        if len(cpf) != 11:
            raise forms.ValidationError("CPF deve conter 11 dígitos.")
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

    def save(self, commit=True):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        user = User.objects.create_user(username=username, password=password)
        perfil = super().save(commit=False)
        perfil.user = user
        perfil.tipo = 'GESTOR'
        
        if commit:
            perfil.save()
        return perfil

class ServidorForm(UsuarioBaseForm, forms.ModelForm):
    class Meta:
        model = Servidor
        fields = ['nome_completo', 'cpf', 'carga_horaria_diaria', 'departamento', 'ativo']
        
    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        cpf = re.sub(r'[^0-9]', '', cpf)
        if len(cpf) != 11:
            raise forms.ValidationError("CPF deve conter 11 dígitos.")
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

    def save(self, commit=True):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        user = User.objects.create_user(username=username, password=password)
        Perfil.objects.create(user=user, tipo='SERVIDOR', departamento=self.cleaned_data.get('departamento'))
        
        servidor = super().save(commit=False)
        servidor.usuario = user
        if commit:
            servidor.save()
        return servidor

class RegistroPontoForm(forms.ModelForm):
    class Meta:
        model = RegistroPonto
        fields = ['servidor', 'data', 'entrada', 'saida']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
            'entrada': forms.TimeInput(attrs={'type': 'time'}),
            'saida': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        entrada = cleaned_data.get('entrada')
        saida = cleaned_data.get('saida')
        
        if entrada and saida and saida <= entrada:
            self.add_error('saida', "O horário de saída deve ser maior que o de entrada.")
        return cleaned_data

class CompensacaoForm(forms.ModelForm):
    TIPO_CHOICES = [
        ('parcial', 'Horas/Minutos Parciais'),
        ('dias', 'Dias Inteiros de Folga'),
    ]
    tipo_compensacao = forms.ChoiceField(choices=TIPO_CHOICES, initial='parcial', widget=forms.RadioSelect)
    
    dias_folga = forms.IntegerField(label="Quantidade de Dias", min_value=1, required=False)
    horas_folga = forms.IntegerField(label="Horas", min_value=0, initial=0, required=False)
    minutos_folga = forms.IntegerField(label="Minutos", min_value=0, max_value=59, initial=0, required=False)
    
    class Meta:
        model = Compensacao
        fields = ['servidor', 'data', 'descricao']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user and hasattr(self.user, 'perfil') and self.user.perfil.tipo == 'SERVIDOR':
            self.fields['servidor'].widget = forms.HiddenInput()
            self.fields['servidor'].required = False

    def clean(self):
        cleaned_data = super().clean()
        servidor = cleaned_data.get('servidor')
        
        # Se for servidor, pega o servidor vinculado ao usuário
        if not servidor and self.user and hasattr(self.user, 'servidor_perfil'):
            servidor = self.user.servidor_perfil
            cleaned_data['servidor'] = servidor

        tipo = cleaned_data.get('tipo_compensacao')
        
        if servidor:
            # Calcular saldo disponível (apenas registros de ponto e compensações APROVADAS)
            total_extras = RegistroPonto.objects.filter(servidor=servidor).aggregate(Sum('saldo_minutos_dia'))['saldo_minutos_dia__sum'] or 0
            total_compensado = Compensacao.objects.filter(servidor=servidor, status='APROVADO').aggregate(Sum('minutos_descontados'))['minutos_descontados__sum'] or 0
            saldo_atual = total_extras - total_compensado
            
            # Calcular minutos a descontar
            minutos_a_descontar = 0
            if tipo == 'dias':
                dias = cleaned_data.get('dias_folga')
                if not dias:
                    self.add_error('dias_folga', "Informe a quantidade de dias.")
                else:
                    minutos_a_descontar = dias * servidor.carga_horaria_diaria * 60
            else:
                horas = cleaned_data.get('horas_folga') or 0
                minutos = cleaned_data.get('minutos_folga') or 0
                minutos_a_descontar = (horas * 60) + minutos
                
                if minutos_a_descontar <= 0:
                    self.add_error('horas_folga', "Informe o tempo a descontar.")

            if minutos_a_descontar > 0 and minutos_a_descontar > saldo_atual:
                saldo_fmt = format_minutos_hhmm(saldo_atual)
                desconto_fmt = format_minutos_hhmm(minutos_a_descontar)
                raise forms.ValidationError(
                    f"Saldo insuficiente! Disponível: {saldo_fmt}. Solicitado: {desconto_fmt}."
                )
            
            cleaned_data['minutos_descontados'] = minutos_a_descontar
            
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.minutos_descontados = self.cleaned_data.get('minutos_descontados')
        
        if self.user and hasattr(self.user, 'perfil'):
            if self.user.perfil.tipo == 'SERVIDOR':
                instance.status = 'PENDENTE'
            else:
                instance.status = 'APROVADO'
        
        if commit:
            instance.save()
        return instance
