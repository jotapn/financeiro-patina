import json
from datetime import date

from langchain.prompts import PromptTemplate

from .llm_manager import get_llm, resolve_model
from .tools import build_tools_for_user

SYSTEM_PROMPT = """
Você é o FinanceFlow AI, assistente financeiro pessoal e familiar.
Você tem acesso em tempo real aos dados financeiros do usuário via ferramentas.

SUAS CAPACIDADES:
- Responder perguntas sobre saldos, gastos, receitas e investimentos com dados reais
- Analisar padrões de gastos e apontar oportunidades de economia
- Alertar sobre orçamentos no limite e faturas próximas do vencimento
- Projetar cenários futuros baseados em dados históricos
- Explicar conceitos financeiros de forma clara e didática
- Calcular metas, prazos e sugestões de aportes

REGRAS:
- Baseie respostas SEMPRE nos dados retornados pelas ferramentas
- Nunca invente dados; use apenas o que as ferramentas retornam
- Seja direto e empático
- Responda SEMPRE em português do Brasil
- Para investimentos: "Não sou assessor financeiro regulamentado. Consulte um profissional para decisões de alto impacto financeiro."
- Respostas objetivas: máximo 300 palavras, salvo análise detalhada pedida
- Formate valores monetários como: R$ 1.234,56
"""


class FinanceFlowAgent:
    def __init__(self, user):
        self.user = user
        self.tools = {tool.name: tool for tool in build_tools_for_user(user)}
        self.llm = get_llm(streaming=True)
        self.prompt = PromptTemplate.from_template(
            '{system_prompt}\n\nHoje: {today}\n\nPergunta do usuário:\n{question}\n\nDados disponíveis:\n{tool_payload}\n\nResponda em português do Brasil.'
        )

    def _select_tool_names(self, question: str):
        lower = question.lower()
        selected = ['get_monthly_summary', 'get_account_balances']
        if any(word in lower for word in ['categoria', 'gastei', 'gasto']):
            selected.append('get_expenses_by_category')
        if any(word in lower for word in ['orçamento', 'orcamento', 'budget']):
            selected.append('get_budget_status')
        if any(word in lower for word in ['fatura', 'cartão', 'cartao']):
            selected.extend(['get_card_info', 'get_upcoming_bills'])
        if any(word in lower for word in ['invest', 'carteira', 'ação', 'acao', 'fii', 'cripto']):
            selected.append('get_investment_portfolio')
        if any(word in lower for word in ['meta', 'objetivo']):
            selected.append('get_financial_goals_status')
        if any(word in lower for word in ['anomalia', 'economizar', 'exagero']):
            selected.append('get_spending_anomalies')
        if any(word in lower for word in ['tendência', 'tendencia', 'fluxo']):
            selected.append('get_cash_flow_trend')
        if any(word in lower for word in ['poupança', 'poupar', 'savings']):
            selected.append('get_savings_rate')
        if any(word in lower for word in ['maiores', 'top']):
            selected.append('get_top_expenses')
        return list(dict.fromkeys(selected))

    def _tool_input(self, tool_name: str):
        today = date.today()
        if tool_name in {
            'get_monthly_summary',
            'get_expenses_by_category',
            'get_budget_status',
            'get_savings_rate',
            'get_spending_anomalies',
        }:
            return {'month': today.month, 'year': today.year}
        return {}

    def _collect_data(self, question: str):
        payload = {}
        for tool_name in self._select_tool_names(question):
            tool = self.tools.get(tool_name)
            if not tool:
                continue
            try:
                payload[tool_name] = tool.invoke(self._tool_input(tool_name))
            except Exception as exc:
                payload[tool_name] = {'error': str(exc)}
        return payload

    def stream(self, payload: dict):
        question = payload.get('input', '')
        tool_payload = self._collect_data(question)
        final_prompt = self.prompt.format(
            system_prompt=SYSTEM_PROMPT,
            today=date.today().isoformat(),
            question=question,
            tool_payload=json.dumps(tool_payload, ensure_ascii=False, indent=2, default=str),
        )
        for chunk in self.llm.stream(final_prompt):
            yield {'output': chunk}


def build_agent_for_user(user):
    return FinanceFlowAgent(user)


def get_model_status():
    resolved = resolve_model()
    labels = {
        'online': 'Online',
        'fallback': 'Online (fallback)',
        'offline': 'Offline',
    }
    return {
        'model': resolved['model'],
        'preferred_model': resolved['preferred_model'],
        'status': labels.get(resolved['status'], resolved['status']),
        'base_url': resolved['base_url'] or '',
        'installed_models': resolved['installed_models'],
        'error': resolved['error'],
    }
