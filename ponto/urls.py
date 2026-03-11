from django.urls import path
from . import views

urlpatterns = [
    # Autenticação
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),

    # Home
    path('', views.HomeView.as_view(), name='home'),

    # Gestão de Departamentos (ADM)
    path('departamentos/', views.DepartamentoListView.as_view(), name='departamento_list'),
    path('departamentos/novo/', views.DepartamentoCreateView.as_view(), name='departamento_add'),
    path('departamentos/<int:pk>/editar/', views.DepartamentoUpdateView.as_view(), name='departamento_edit'),

    # Gestão de Gestores (ADM)
    path('gestores/', views.GestorListView.as_view(), name='gestor_list'),
    path('gestores/novo/', views.GestorCreateView.as_view(), name='gestor_add'),

    # Gestão de Servidores (ADM/Gestor)
    path('servidores/', views.ServidorListView.as_view(), name='servidor_list'),
    path('servidores/novo/', views.ServidorCreateView.as_view(), name='servidor_add'),
    path('servidores/<int:pk>/editar/', views.ServidorUpdateView.as_view(), name='servidor_edit'),
    path('servidores/<int:pk>/excluir/', views.ServidorDeleteView.as_view(), name='servidor_delete'),

    # Movimentação (Gestor/Servidor)
    path('ponto/registrar/', views.RegistroPontoCreateView.as_view(), name='ponto_add'),
    path('ponto/folga/', views.CompensacaoCreateView.as_view(), name='compensacao_add'),
    path('ponto/pendentes/', views.CompensacoesPendentesView.as_view(), name='compensacoes_pendentes'),
    path('ponto/<int:pk>/aprovar/', views.AprovarCompensacaoView.as_view(), name='aprovar_compensacao'),

    # Relatórios
    path('relatorio/', views.RelatorioGeralView.as_view(), name='relatorio_geral'),
    path('relatorio/pdf/', views.RelatorioGeralPDFView.as_view(), name='relatorio_geral_pdf'),
    path('relatorio/servidor/<int:pk>/', views.RelatorioServidorView.as_view(), name='relatorio_servidor'),
    path('relatorio/servidor/<int:pk>/pdf/', views.RelatorioServidorPDFView.as_view(), name='relatorio_servidor_pdf'),
]
