# Sistema de Controle de Banco de Horas

Sistema web desenvolvido em Python/Django para contabilizar o banco de horas de servidores públicos.

## Funcionalidades
- Cadastro de servidores com carga horária específica (4h, 6h, 8h, 12h).
- Registro diário de ponto (entrada e saída).
- Cálculo automático de saldo em minutos (extra (+) ou débito (-)).
- Relatório mensal de saldos por servidor.
- Extrato individual detalhado com saldo geral acumulado.

## Como rodar localmente

1. **Clone ou extraia o projeto** para uma pasta.
2. **Crie um ambiente virtual**:
   ```bash
   python -m venv venv
   ```
3. **Ative o ambiente virtual**:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Execute as migrações do banco de dados**:
   ```bash
   python manage.py migrate
   ```
6. **Crie um superusuário (Admin)**:
   ```bash
   python manage.py createsuperuser
   ```
7. **Inicie o servidor**:
   ```bash
   python manage.py runserver
   ```
8. **Acesse no navegador**: `http://127.0.0.1:8000`

## Dados de Exemplo
Para carregar dados de exemplo (servidores e registros de teste), execute:
```bash
python manage.py loaddata demo_data.json
```
*(Certifique-se de que o arquivo demo_data.json está na raiz do projeto)*

## Tecnologias Utilizadas
- Python 3
- Django 6
- Bootstrap 5
- SQLite (Padrão)
