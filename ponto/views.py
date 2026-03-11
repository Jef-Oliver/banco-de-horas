from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, CreateView, UpdateView, DetailView, TemplateView, DeleteView, View
from django.urls import reverse_lazy
from django.db.models import Sum, Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from .models import Servidor, RegistroPonto, Compensacao, Departamento, Perfil
from .forms import ServidorForm, RegistroPontoForm, CompensacaoForm, DepartamentoForm, GestorForm
from .utils import format_minutos_hhmm
from datetime import datetime

# --- Mixins de Permissão ---

class AdmRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and hasattr(self.request.user, 'perfil') and self.request.user.perfil.tipo == 'ADM'

class GestorRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and hasattr(self.request.user, 'perfil') and self.request.user.perfil.tipo in ['ADM', 'GESTOR']

# --- Views de Autenticação ---

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('login')

# --- Views do Sistema ---

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'ponto/home.html'
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            try:
                perfil = request.user.perfil
                if perfil.tipo == 'SERVIDOR':
                     return redirect('relatorio_servidor', pk=request.user.servidor_perfil.pk)
            except:
                pass
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        perfil = self.request.user.perfil
        servidores_qs = Servidor.objects.filter(ativo=True)
        
        if perfil.tipo == 'GESTOR':
            servidores_qs = servidores_qs.filter(departamento=perfil.departamento)

        context['total_servidores'] = servidores_qs.count()
        return context

class ServidorListView(LoginRequiredMixin, GestorRequiredMixin, ListView):
    model = Servidor
    template_name = 'ponto/servidor_list.html'
    context_object_name = 'servidores'

    def get_queryset(self):
        qs = super().get_queryset()
        perfil = self.request.user.perfil
        if perfil.tipo == 'GESTOR':
            return qs.filter(departamento=perfil.departamento)
        return qs

class ServidorCreateView(LoginRequiredMixin, GestorRequiredMixin, CreateView):
    model = Servidor
    form_class = ServidorForm
    template_name = 'ponto/servidor_form.html'
    success_url = reverse_lazy('servidor_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        perfil = self.request.user.perfil
        if perfil.tipo == 'GESTOR':
            # Gestor só pode cadastrar no seu departamento
            form.fields['departamento'].queryset = Departamento.objects.filter(id=perfil.departamento.id)
            form.fields['departamento'].initial = perfil.departamento
        return form

class ServidorUpdateView(LoginRequiredMixin, GestorRequiredMixin, UpdateView):
    model = Servidor
    form_class = ServidorForm
    template_name = 'ponto/servidor_form.html'
    success_url = reverse_lazy('servidor_list')

    def get_queryset(self):
        qs = super().get_queryset()
        perfil = self.request.user.perfil
        if perfil.tipo == 'GESTOR':
            return qs.filter(departamento=perfil.departamento)
        return qs

class ServidorDeleteView(LoginRequiredMixin, AdmRequiredMixin, DeleteView):
    model = Servidor
    template_name = 'ponto/servidor_confirm_delete.html'
    success_url = reverse_lazy('servidor_list')

class RegistroPontoCreateView(LoginRequiredMixin, GestorRequiredMixin, CreateView):
    model = RegistroPonto
    form_class = RegistroPontoForm
    template_name = 'ponto/ponto_form.html'
    success_url = reverse_lazy('relatorio_geral')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        perfil = self.request.user.perfil
        if perfil.tipo == 'GESTOR':
            form.fields['servidor'].queryset = Servidor.objects.filter(departamento=perfil.departamento)
        return form

class CompensacaoCreateView(LoginRequiredMixin, CreateView):
    model = Compensacao
    form_class = CompensacaoForm
    template_name = 'ponto/compensacao_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_success_url(self):
        if self.request.user.perfil.tipo == 'SERVIDOR':
            return reverse_lazy('relatorio_servidor', kwargs={'pk': self.request.user.servidor_perfil.pk})
        return reverse_lazy('relatorio_geral')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        perfil = self.request.user.perfil
        if perfil.tipo == 'GESTOR':
            form.fields['servidor'].queryset = Servidor.objects.filter(departamento=perfil.departamento)
        elif perfil.tipo == 'SERVIDOR':
            # Servidor já é tratado no __init__ do form (HiddenInput)
            pass
        return form

    def get_initial(self):
        initial = super().get_initial()
        servidor_id = self.request.GET.get('servidor')
        if servidor_id:
            initial['servidor'] = servidor_id
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        perfil = self.request.user.perfil
        
        if perfil.tipo == 'SERVIDOR':
            servidor = self.request.user.servidor_perfil
            total_extras = RegistroPonto.objects.filter(servidor=servidor).aggregate(Sum('saldo_minutos_dia'))['saldo_minutos_dia__sum'] or 0
            total_compensado = Compensacao.objects.filter(servidor=servidor, status='APROVADO').aggregate(Sum('minutos_descontados'))['minutos_descontados__sum'] or 0
            context['saldo_atual'] = format_minutos_hhmm(total_extras - total_compensado)
            return context

        servidores_qs = Servidor.objects.all()
        if perfil.tipo == 'GESTOR':
            servidores_qs = servidores_qs.filter(departamento=perfil.departamento)
            
        saldos = {}
        for servidor in servidores_qs:
            total_extras = RegistroPonto.objects.filter(servidor=servidor).aggregate(Sum('saldo_minutos_dia'))['saldo_minutos_dia__sum'] or 0
            total_compensado = Compensacao.objects.filter(servidor=servidor, status='APROVADO').aggregate(Sum('minutos_descontados'))['minutos_descontados__sum'] or 0
            saldos[servidor.pk] = format_minutos_hhmm(total_extras - total_compensado)
        context['saldos_servidores'] = saldos
        return context

class CompensacoesPendentesView(LoginRequiredMixin, GestorRequiredMixin, ListView):
    model = Compensacao
    template_name = 'ponto/compensacoes_pendentes.html'
    context_object_name = 'pendentes'

    def get_queryset(self):
        perfil = self.request.user.perfil
        qs = Compensacao.objects.filter(status='PENDENTE')
        if perfil.tipo == 'GESTOR':
            qs = qs.filter(servidor__departamento=perfil.departamento)
        return qs

class AprovarCompensacaoView(LoginRequiredMixin, GestorRequiredMixin, View):
    def post(self, request, pk):
        compensacao = get_object_or_404(Compensacao, pk=pk)
        perfil = request.user.perfil
        
        # Verificar se o gestor tem permissão sobre este servidor
        if perfil.tipo == 'GESTOR' and compensacao.servidor.departamento != perfil.departamento:
            messages.error(request, "Sem permissão para aprovar esta solicitação.")
            return redirect('compensacoes_pendentes')
            
        acao = request.POST.get('acao')
        if acao == 'aprovar':
            compensacao.status = 'APROVADO'
            messages.success(request, f"Solicitação de {compensacao.servidor.nome_completo} aprovada.")
        elif acao == 'rejeitar':
            compensacao.status = 'REJEITADO'
            messages.success(request, f"Solicitação de {compensacao.servidor.nome_completo} rejeitada.")
        
        compensacao.save()
        return redirect('compensacoes_pendentes')

class RelatorioGeralView(LoginRequiredMixin, GestorRequiredMixin, ListView):
    model = Servidor
    template_name = 'ponto/relatorio_geral.html'
    context_object_name = 'servidores'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        perfil = self.request.user.perfil
        mes = self.request.GET.get('mes', datetime.now().month)
        ano = self.request.GET.get('ano', datetime.now().year)
        
        servidores_qs = Servidor.objects.all()
        if perfil.tipo == 'GESTOR':
            servidores_qs = servidores_qs.filter(departamento=perfil.departamento)
        
        servidores_data = []
        for servidor in servidores_qs:
            filtros = Q(servidor=servidor)
            if mes and ano:
                filtros &= Q(data__month=mes, data__year=ano)
            
            saldo_extras = RegistroPonto.objects.filter(filtros).aggregate(Sum('saldo_minutos_dia'))['saldo_minutos_dia__sum'] or 0
            saldo_compensado = Compensacao.objects.filter(filtros, status='APROVADO').aggregate(Sum('minutos_descontados'))['minutos_descontados__sum'] or 0
            saldo_total = saldo_extras - saldo_compensado
            
            servidores_data.append({
                'servidor': servidor,
                'saldo_formatado': format_minutos_hhmm(saldo_total),
                'saldo_raw': saldo_total
            })
            
        context['servidores_data'] = servidores_data
        context['mes_atual'] = int(mes)
        context['ano_atual'] = int(ano)
        context['meses'] = range(1, 13)
        context['anos'] = range(datetime.now().year - 2, datetime.now().year + 2)
        return context

class RelatorioServidorView(LoginRequiredMixin, DetailView):
    model = Servidor
    template_name = 'ponto/relatorio_servidor.html'
    context_object_name = 'servidor'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        perfil = self.request.user.perfil
        # Servidor só vê o seu. Gestor vê do seu setor. ADM vê tudo.
        if perfil.tipo == 'SERVIDOR' and obj.usuario != self.request.user:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        if perfil.tipo == 'GESTOR' and obj.departamento != perfil.departamento:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        servidor = self.get_object()
        mes = self.request.GET.get('mes', datetime.now().month)
        ano = self.request.GET.get('ano', datetime.now().year)
        
        registros = RegistroPonto.objects.filter(servidor=servidor, data__month=mes, data__year=ano).order_by('data')
        
        extrato = []
        for r in registros:
            extrato.append({
                'data': r.data,
                'entrada': r.entrada,
                'saida': r.saida,
                'trabalhadas': format_minutos_hhmm(r.minutos_trabalhados),
                'saldo_dia': format_minutos_hhmm(r.saldo_minutos_dia),
            })
            
        total_extras_geral = RegistroPonto.objects.filter(servidor=servidor).aggregate(Sum('saldo_minutos_dia'))['saldo_minutos_dia__sum'] or 0
        total_compensado_geral = Compensacao.objects.filter(servidor=servidor, status='APROVADO').aggregate(Sum('minutos_descontados'))['minutos_descontados__sum'] or 0
        saldo_geral = total_extras_geral - total_compensado_geral
        
        total_extras_mes = registros.aggregate(Sum('saldo_minutos_dia'))['saldo_minutos_dia__sum'] or 0
        total_compensado_mes = Compensacao.objects.filter(servidor=servidor, data__month=mes, data__year=ano, status='APROVADO').aggregate(Sum('minutos_descontados'))['minutos_descontados__sum'] or 0
        saldo_mes = total_extras_mes - total_compensado_mes
        
        context.update({
            'extrato': extrato,
            'compensacoes': Compensacao.objects.filter(servidor=servidor, data__month=mes, data__year=ano).order_by('data'),
            'saldo_mes_formatado': format_minutos_hhmm(saldo_mes),
            'saldo_geral_formatado': format_minutos_hhmm(saldo_geral),
            'mes_atual': int(mes),
            'ano_atual': int(ano),
            'meses': range(1, 13),
            'anos': range(datetime.now().year - 2, datetime.now().year + 2),
        })
        return context

# --- Views de Gestão (ADM) ---

class DepartamentoListView(LoginRequiredMixin, AdmRequiredMixin, ListView):
    model = Departamento
    template_name = 'ponto/departamento_list.html'
    context_object_name = 'departamentos'

class DepartamentoCreateView(LoginRequiredMixin, AdmRequiredMixin, CreateView):
    model = Departamento
    form_class = DepartamentoForm
    template_name = 'ponto/departamento_form.html'
    success_url = reverse_lazy('departamento_list')

class DepartamentoUpdateView(LoginRequiredMixin, AdmRequiredMixin, UpdateView):
    model = Departamento
    form_class = DepartamentoForm
    template_name = 'ponto/departamento_form.html'
    success_url = reverse_lazy('departamento_list')

class GestorListView(LoginRequiredMixin, AdmRequiredMixin, ListView):
    model = Perfil
    template_name = 'ponto/gestor_list.html'
    context_object_name = 'gestores'

    def get_queryset(self):
        return Perfil.objects.filter(tipo='GESTOR')

class GestorCreateView(LoginRequiredMixin, AdmRequiredMixin, CreateView):
    model = Perfil
    form_class = GestorForm
    template_name = 'ponto/gestor_form.html'
    success_url = reverse_lazy('gestor_list')

# --- Views de PDF ---

from .pdf_utils import render_to_pdf

class RelatorioGeralPDFView(RelatorioGeralView):
    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return render_to_pdf('ponto/relatorio_geral_pdf.html', context)

class RelatorioServidorPDFView(RelatorioServidorView):
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data()
        return render_to_pdf('ponto/relatorio_servidor_pdf.html', context)
