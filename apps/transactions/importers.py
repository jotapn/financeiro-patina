import csv
import io
from datetime import datetime
from decimal import Decimal

from .models import Transaction


class CSVImporter:
    def _read_text(self, file):
        file.seek(0)
        content = file.read()
        if isinstance(content, bytes):
            for encoding in ('utf-8-sig', 'latin-1', 'utf-8'):
                try:
                    return content.decode(encoding)
                except UnicodeDecodeError:
                    continue
            return content.decode('utf-8', errors='ignore')
        return content

    def detect_bank(self, file) -> str:
        text = self._read_text(file)
        sample = '\n'.join(text.splitlines()[:3])
        lower = sample.lower()
        if 'date,category,title,amount' in lower:
            return 'nubank'
        if 'data,descrição,valor' in lower or 'data,descricao,valor' in lower:
            return 'inter'
        if ';' in sample and 'Histórico' in sample and 'Crédito' in sample and 'Débito' in sample:
            return 'bradesco'
        return 'generic'

    def parse(self, file, bank_type) -> list[dict]:
        text = self._read_text(file)
        delimiter = ';' if bank_type == 'bradesco' else ','
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        rows = []
        for row in reader:
            parsed = self._normalize_row(row, bank_type)
            if parsed and parsed['date'] and parsed['description']:
                rows.append(parsed)
        return rows

    def _parse_date(self, raw):
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y'):
            try:
                return datetime.strptime(str(raw).strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _parse_decimal(self, raw):
        raw = str(raw or '').strip().replace('R$', '').replace('.', '').replace(',', '.')
        if not raw:
            return Decimal('0')
        return Decimal(raw)

    def _normalize_row(self, row, bank_type):
        if bank_type == 'nubank':
            amount = self._parse_decimal(row.get('amount'))
            return {'date': self._parse_date(row.get('date')), 'description': row.get('title', '').strip(), 'category_hint': row.get('category', '').strip(), 'amount': abs(amount), 'transaction_type': 'income' if amount > 0 else 'expense'}
        if bank_type == 'inter':
            amount = self._parse_decimal(row.get('Valor'))
            return {'date': self._parse_date(row.get('Data')), 'description': row.get('Descrição', row.get('Descricao', '')).strip(), 'category_hint': '', 'amount': abs(amount), 'transaction_type': 'income' if amount > 0 else 'expense'}
        if bank_type == 'bradesco':
            credit = self._parse_decimal(row.get('Crédito'))
            debit = self._parse_decimal(row.get('Débito'))
            amount = credit if credit else debit
            return {'date': self._parse_date(row.get('Data')), 'description': row.get('Histórico', '').strip(), 'category_hint': '', 'amount': abs(amount), 'transaction_type': 'income' if credit else 'expense'}
        keys = list(row.keys())
        description = row.get('description') or row.get('Descrição') or row.get('Descricao') or row.get(keys[1] if len(keys) > 1 else '')
        amount = self._parse_decimal(row.get('amount') or row.get('Valor') or row.get(keys[-1] if keys else '0'))
        return {'date': self._parse_date(row.get('date') or row.get('Data') or row.get(keys[0] if keys else '')), 'description': str(description or '').strip(), 'category_hint': '', 'amount': abs(amount), 'transaction_type': 'income' if amount > 0 else 'expense'}

    def detect_duplicates(self, transactions, user) -> list[dict]:
        duplicates = []
        for row in transactions:
            exists = Transaction.objects.filter(user=user, date=row['date'], amount=row['amount'], description__iexact=row['description']).exists()
            row['is_duplicate'] = exists
            if exists:
                duplicates.append(row)
        return duplicates
