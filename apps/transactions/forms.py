from datetime import date

from django import forms
from django.db.models import Q

from apps.accounts.models import FinancialAccount, PaymentMethod
from apps.cards.models import CreditCard
from apps.categories.models import Category, Subcategory
from apps.core.security import validate_upload_file

from .models import Tag, Transaction


class PaymentMethodChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.get_method_type_display()


class PaymentMethodSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        option_value = getattr(value, 'value', value)
        if option_value and hasattr(self.choices, 'queryset'):
            try:
                method = self.choices.queryset.get(pk=option_value)
                option['attrs']['data-method-type'] = method.method_type
            except PaymentMethod.DoesNotExist:
                pass
        return option


class SubcategorySelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        option_value = getattr(value, 'value', value)
        if option_value and hasattr(self.choices, 'queryset'):
            try:
                subcategory = self.choices.queryset.select_related('category').get(pk=option_value)
                option['attrs']['data-category-id'] = str(subcategory.category_id)
            except Subcategory.DoesNotExist:
                pass
        return option


class TransactionForm(forms.ModelForm):
    payment_method = PaymentMethodChoiceField(
        queryset=PaymentMethod.objects.none(),
        required=False,
        label='Metodo de pagamento',
        widget=PaymentMethodSelect(
            attrs={
                'x-model': 'selectedPaymentMethod',
                'x-ref': 'paymentMethodSelect',
                '@change': 'updatePaymentType()',
            }
        ),
    )

    class Meta:
        model = Transaction
        fields = [
            'description',
            'amount',
            'transaction_type',
            'date',
            'payment_method',
            'account',
            'credit_card',
            'category',
            'subcategory',
            'status',
            'due_date',
            'notes',
            'location',
            'receipt_image',
            'tags',
            'installment_number',
            'installment_total',
        ]
        labels = {
            'description': 'Descricao',
            'amount': 'Valor',
            'transaction_type': 'Tipo de transacao',
            'date': 'Data',
            'account': 'Conta',
            'credit_card': 'Cartao de credito',
            'category': 'Categoria',
            'subcategory': 'Subcategoria',
            'status': 'Status',
            'due_date': 'Data de vencimento',
            'notes': 'Observacoes',
            'location': 'Estabelecimento',
            'receipt_image': 'Comprovante',
            'tags': 'Tags',
            'installment_number': 'Numero da parcela',
            'installment_total': 'Total de parcelas',
        }
        widgets = {
            'description': forms.TextInput(attrs={'placeholder': 'Ex.: Supermercado do mes', 'class': 'input-glass'}),
            'amount': forms.NumberInput(
                attrs={
                    'step': '0.01',
                    'placeholder': '0.00',
                    'inputmode': 'decimal',
                    'class': 'input-glass input-with-prefix',
                }
            ),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'input-glass'}, format='%Y-%m-%d'),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'input-glass'}, format='%Y-%m-%d'),
            'notes': forms.Textarea(
                attrs={'rows': 3, 'placeholder': 'Detalhes adicionais da transacao', 'class': 'input-glass'}
            ),
            'location': forms.TextInput(attrs={'placeholder': 'Ex.: Mercado Central', 'class': 'input-glass'}),
            'receipt_image': forms.ClearableFileInput(attrs={'class': 'input-glass'}),
            'installment_number': forms.NumberInput(attrs={'min': 1, 'placeholder': '1', 'class': 'input-glass'}),
            'installment_total': forms.NumberInput(attrs={'min': 1, 'placeholder': '1', 'class': 'input-glass'}),
            'subcategory': SubcategorySelect(attrs={'x-ref': 'subcategorySelect'}),
        }

    def __init__(self, *args, family_group=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.family_group = family_group

        if family_group:
            self.fields['account'].queryset = FinancialAccount.objects.filter(
                family_group=family_group, is_active=True
            ).order_by('name')
            self.fields['credit_card'].queryset = CreditCard.objects.filter(
                family_group=family_group, is_active=True
            ).order_by('name')
            self.fields['payment_method'].queryset = PaymentMethod.objects.filter(
                family_group=family_group, is_active=True
            ).order_by('name')
            self.fields['category'].queryset = Category.objects.filter(
                Q(family_group=family_group) | Q(is_system=True)
            ).order_by('name')
            self.fields['subcategory'].queryset = Subcategory.objects.filter(
                Q(category__family_group=family_group) | Q(category__is_system=True)
            ).select_related('category').order_by('category__name', 'name')
            self.fields['tags'].queryset = Tag.objects.filter(family_group=family_group).order_by('name')

        self.fields['date'].initial = date.today

        required = {'description', 'amount', 'transaction_type', 'date', 'category'}
        for name, field in self.fields.items():
            field.required = name in required
            field.widget.attrs.setdefault('class', 'input-glass')

        self.fields['transaction_type'].choices = [('', 'Selecione o tipo')] + [
            choice for choice in self.fields['transaction_type'].choices if choice[0]
        ]
        self.fields['status'].choices = [choice for choice in self.fields['status'].choices if choice[0]]

        self.fields['account'].empty_label = 'Selecione a conta'
        self.fields['credit_card'].empty_label = 'Selecione o cartao'
        self.fields['category'].empty_label = 'Selecione a categoria'
        self.fields['subcategory'].empty_label = 'Selecione a subcategoria'
        self.fields['payment_method'].empty_label = 'Selecione o metodo'

        self.fields['transaction_type'].widget.attrs.update(
            {'x-model': 'transactionType', '@change': 'filterPaymentMethods()'}
        )
        self.fields['status'].widget.attrs.update({'x-model': 'transactionStatus'})
        self.fields['payment_method'].widget.attrs.update(
            {'x-model': 'selectedPaymentMethod', 'x-ref': 'paymentMethodSelect', '@change': 'updatePaymentType()'}
        )
        self.fields['credit_card'].widget.attrs.update({'x-model': 'selectedCard'})
        self.fields['category'].widget.attrs.update(
            {'x-model': 'selectedCategory', '@change': 'filterSubcategories()'}
        )
        self.fields['subcategory'].widget.attrs.update({'x-ref': 'subcategorySelect'})

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        account = cleaned_data.get('account')
        credit_card = cleaned_data.get('credit_card')
        category = cleaned_data.get('category')
        subcategory = cleaned_data.get('subcategory')
        transaction_type = cleaned_data.get('transaction_type')

        if payment_method and payment_method.method_type == 'credit':
            if transaction_type == 'income':
                self.add_error('payment_method', 'Receitas nao podem usar cartao de credito como metodo de pagamento.')
            cleaned_data['account'] = None
            cleaned_data['status'] = 'paid'
            cleaned_data['due_date'] = None
            if not credit_card:
                self.add_error('credit_card', 'Selecione o cartao para pagamentos no credito.')
        else:
            cleaned_data['credit_card'] = None

        if subcategory and category and subcategory.category_id != category.id:
            self.add_error('subcategory', 'Selecione uma subcategoria da categoria informada.')

        if subcategory and not category:
            self.add_error('category', 'Selecione a categoria antes da subcategoria.')

        return cleaned_data

    def clean_receipt_image(self):
        receipt_image = self.cleaned_data.get('receipt_image')
        validate_upload_file(receipt_image)
        return receipt_image
