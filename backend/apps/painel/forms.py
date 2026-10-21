import re
from decimal import Decimal
from django import forms
from django.forms import BaseModelFormSet, inlineformset_factory, modelformset_factory
from django.utils.text import slugify
from apps.catalog.models import Category, PizzaCrust, Product, ProductSizePrice
from apps.delivery.models import DeliveryZone, Employee, OperatingHour, SalaryAdvance, StoreSettings
from apps.promotions.models import Promotion

HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
WEEKDAYS = [  # Python convention (0=Monday), the one Promotion.is_currently_valid uses
    (0, "Seg"), (1, "Ter"), (2, "Qua"), (3, "Qui"), (4, "Sex"), (5, "Sáb"), (6, "Dom"),
]


def _non_negative(value, label="O valor"):
    if value is not None and value < 0:
        raise forms.ValidationError(f"{label} não pode ser negativo.")
    return value


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name", "category", "product_type", "price_category", "description",
            "base_price", "price_text", "tag", "is_highlight", "is_available",
            "display_order", "photo_url", "image",
        ]
        labels = {
            "name": "Nome",
            "category": "Categoria",
            "product_type": "Tipo",
            "price_category": "Faixa de preço (pizzas)",
            "description": "Descrição / ingredientes",
            "base_price": "Preço (R$)",
            "price_text": "Texto de preço exibido",
            "tag": "Selo",
            "is_highlight": "Destaque na vitrine",
            "is_available": "Disponível para pedidos",
            "display_order": "Ordem de exibição",
            "photo_url": "Caminho da foto no site",
            "image": "Ou envie uma foto",
        }
        help_texts = {
            "base_price": "Deixe em branco para \"Sob consulta\". Para pizzas o preço vem da tabela de tamanhos abaixo.",
            "price_text": "Ex.: R$ 44,90 ou A partir de R$ 45,90. Em branco, é gerado a partir do preço.",
            "photo_url": "Ex.: /images/cardapio/calabresa-artesanal.webp",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self.fields["category"].queryset = Category.objects.filter(tenant=tenant).order_by("display_order", "name")

    def clean_base_price(self):
        return _non_negative(self.cleaned_data.get("base_price"), "O preço")

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("price_text") and cleaned.get("base_price") is not None:
            cleaned["price_text"] = f"R$ {cleaned['base_price']:.2f}".replace(".", ",")
        elif not cleaned.get("price_text") and cleaned.get("product_type") != Product.ProductType.PIZZA:
            cleaned["price_text"] = "Sob consulta"
        return cleaned

    def save(self, commit=True):
        product = super().save(commit=False)
        product.tenant = self.tenant
        if not product.slug:
            base = slugify(product.name)[:140] or "produto"
            slug, n = base, 2
            while Product.objects.filter(tenant=self.tenant, slug=slug).exists():
                slug, n = f"{base}-{n}", n + 1
            product.slug = slug
        if commit:
            product.save()
        return product


class SizePriceForm(forms.ModelForm):
    class Meta:
        model = ProductSizePrice
        fields = ["size_id", "size_name", "slices", "max_flavors", "price"]
        labels = {
            "size_id": "Código",
            "size_name": "Nome do tamanho",
            "slices": "Fatias",
            "max_flavors": "Máx. sabores",
            "price": "Preço (R$)",
        }

    def clean_price(self):
        return _non_negative(self.cleaned_data.get("price"), "O preço")

    def clean_size_id(self):
        return (self.cleaned_data.get("size_id") or "").strip().lower()


SizePriceFormSet = inlineformset_factory(
    Product, ProductSizePrice, form=SizePriceForm, extra=0, can_delete=True,
)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description", "display_order", "is_active"]
        labels = {"name": "Nome", "description": "Descrição", "display_order": "Ordem", "is_active": "Visível no site"}


CategoryFormSet = modelformset_factory(Category, form=CategoryForm, extra=0)


class CrustForm(forms.ModelForm):
    class Meta:
        model = PizzaCrust
        fields = ["name", "price", "price_text", "is_active", "display_order"]
        labels = {
            "name": "Borda", "price": "Preço (R$)", "price_text": "Texto exibido",
            "is_active": "Disponível", "display_order": "Ordem",
        }

    def clean_price(self):
        return _non_negative(self.cleaned_data.get("price"), "O preço")

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("price_text") and cleaned.get("price") is not None:
            price = cleaned["price"]
            cleaned["price_text"] = "Grátis" if price == 0 else f"+ R$ {price:.2f}".replace(".", ",")
        return cleaned


class TenantFormSet(BaseModelFormSet):
    """Model formset whose new rows belong to the panel's establishment."""

    def __init__(self, *args, tenant=None, **kwargs):
        self.tenant = tenant
        super().__init__(*args, **kwargs)

    def save_new(self, form, commit=True):
        obj = form.save(commit=False)
        obj.tenant = self.tenant
        if hasattr(obj, "slug") and not obj.slug:
            obj.slug = slugify(obj.name)[:90] or "item"
        if commit:
            obj.save()
        return obj


CrustFormSet = modelformset_factory(PizzaCrust, form=CrustForm, formset=TenantFormSet, extra=1)


class DeliveryZoneForm(forms.ModelForm):
    class Meta:
        model = DeliveryZone
        fields = ["neighborhood", "city", "fee", "estimated_minutes", "is_active"]
        labels = {
            "neighborhood": "Bairro", "city": "Cidade", "fee": "Taxa (R$)",
            "estimated_minutes": "Tempo (min)", "is_active": "Atendido",
        }

    def clean_fee(self):
        return _non_negative(self.cleaned_data.get("fee"), "A taxa")


DeliveryZoneFormSet = modelformset_factory(
    DeliveryZone, form=DeliveryZoneForm, formset=TenantFormSet, extra=1, can_delete=True,
)


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ["name", "role", "phone", "is_active"]
        labels = {"name": "Nome", "role": "Função", "phone": "WhatsApp", "is_active": "Na equipe"}
        widgets = {"phone": forms.TextInput(attrs={"type": "tel", "placeholder": "(65) 99999-0000"})}

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        if self.instance._state.adding:  # pk is a UUID with a default, so it is set even before saving
            # New people join the team; an absent checkbox would otherwise save them as inactive
            self.fields.pop("is_active", None)

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())
        clash = Employee.objects.filter(tenant=self.tenant, name__iexact=name).exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError("Já existe um funcionário com este nome.")
        return name

    def clean_phone(self):
        digits = "".join(filter(str.isdigit, self.cleaned_data.get("phone") or ""))
        if digits and len(digits) not in (10, 11):
            raise forms.ValidationError("Informe o DDD e o número.")
        return digits

    def save(self, commit=True):
        employee = super().save(commit=False)
        employee.tenant = self.tenant
        if commit:
            employee.save()
        return employee


class CourierForm(EmployeeForm):
    """Quick registration on the couriers page: the role is always courier."""
    class Meta(EmployeeForm.Meta):
        fields = ["name", "phone"]

    def save(self, commit=True):
        self.instance.role = Employee.Role.COURIER
        return super().save(commit)


class SalaryAdvanceForm(forms.ModelForm):
    class Meta:
        model = SalaryAdvance
        fields = ["employee", "amount", "date", "notes"]
        labels = {"employee": "Funcionário", "amount": "Valor (R$)", "date": "Data", "notes": "Observação"}
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "notes": forms.TextInput(attrs={"placeholder": "Opcional"}),
        }

    def __init__(self, *args, tenant=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.tenant = tenant
        self.fields["employee"].queryset = Employee.objects.filter(tenant=tenant, is_active=True)
        self.fields["employee"].empty_label = "Escolha..."

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")
        if amount is not None and amount <= 0:
            raise forms.ValidationError("O valor precisa ser maior que zero.")
        return amount

    def save(self, commit=True):
        advance = super().save(commit=False)
        advance.tenant = self.tenant
        if commit:
            advance.save()
        return advance


class StoreSettingsForm(forms.ModelForm):
    class Meta:
        model = StoreSettings
        fields = [
            "emergency_closed", "emergency_closed_reason", "minimum_order",
            "delivery_time_text", "pickup_time_text",
            "pix_key", "pix_type", "pix_holder", "pix_instructions",
        ]
        labels = {
            "emergency_closed": "Fechar a loja agora (feriado, chuva, imprevisto)",
            "emergency_closed_reason": "Motivo mostrado ao cliente",
            "minimum_order": "Pedido mínimo (R$)",
            "delivery_time_text": "Tempo médio de entrega",
            "pickup_time_text": "Tempo médio de retirada",
            "pix_key": "Chave PIX",
            "pix_type": "Tipo da chave",
            "pix_holder": "Titular",
            "pix_instructions": "Instruções do PIX",
        }
        widgets = {"pix_instructions": forms.Textarea(attrs={"rows": 3})}

    def clean_minimum_order(self):
        return _non_negative(self.cleaned_data.get("minimum_order"), "O pedido mínimo")


class OperatingHourForm(forms.ModelForm):
    class Meta:
        model = OperatingHour
        fields = ["opening_time", "closing_time", "cutoff_time", "is_active"]
        labels = {
            "opening_time": "Abre", "closing_time": "Fecha",
            "cutoff_time": "Corte da cozinha", "is_active": "Abre neste dia",
        }
        widgets = {
            "opening_time": forms.TimeInput(attrs={"type": "time"}),
            "closing_time": forms.TimeInput(attrs={"type": "time"}),
            "cutoff_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned = super().clean()
        for field in ("opening_time", "closing_time", "cutoff_time"):
            value = (cleaned.get(field) or "")[:5]
            if not HHMM.match(value):
                self.add_error(field, "Use o formato HH:MM.")
            cleaned[field] = value
        if not self.errors and cleaned["closing_time"] <= cleaned["opening_time"]:
            self.add_error("closing_time", "O fechamento precisa ser depois da abertura.")
        return cleaned


OperatingHourFormSet = modelformset_factory(OperatingHour, form=OperatingHourForm, extra=0)


class PromotionForm(forms.ModelForm):
    weekdays_allowed = forms.TypedMultipleChoiceField(
        choices=WEEKDAYS, coerce=int, required=False, widget=forms.CheckboxSelectMultiple,
        label="Dias da semana", help_text="Nenhum marcado = vale todos os dias.",
    )

    class Meta:
        model = Promotion
        fields = [
            "title", "description", "coupon_code", "discount_type", "discount_value",
            "min_order_value", "registered_customers_only", "weekdays_allowed",
            "start_date", "end_date", "max_uses", "is_active", "show_top_banner", "banner_text",
        ]
        labels = {
            "title": "Nome da campanha",
            "description": "Descrição",
            "coupon_code": "Código do cupom",
            "discount_type": "Tipo de desconto",
            "discount_value": "Valor do desconto",
            "min_order_value": "Pedido mínimo para usar (R$)",
            "registered_customers_only": "Só para clientes do Clube VIP (logados)",
            "start_date": "Começa em",
            "end_date": "Termina em",
            "max_uses": "Limite de usos",
            "is_active": "Ativa",
            "show_top_banner": "Mostrar faixa no topo do site",
            "banner_text": "Texto da faixa",
        }
        help_texts = {
            "coupon_code": "Em branco = promoção sem cupom.",
            "discount_value": "Em % ou em R$, conforme o tipo.",
            "max_uses": "Em branco = sem limite.",
            "show_top_banner": "O desconto passa a valer automaticamente em todo pedido do site enquanto a promoção estiver válida.",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def clean_coupon_code(self):
        code = (self.cleaned_data.get("coupon_code") or "").strip().upper()
        if not code:
            return None
        if not re.match(r"^[A-Z0-9_-]{3,30}$", code):
            raise forms.ValidationError("Use de 3 a 30 letras, números, - ou _ (sem espaços).")
        clash = Promotion.objects.filter(coupon_code__iexact=code)
        if self.instance.pk:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise forms.ValidationError("Já existe uma promoção com este cupom.")
        return code

    def clean(self):
        cleaned = super().clean()
        value = cleaned.get("discount_value")
        if value is not None:
            if value <= 0:
                self.add_error("discount_value", "O desconto precisa ser maior que zero.")
            elif cleaned.get("discount_type") == Promotion.DiscountType.PERCENTAGE and value > Decimal("100"):
                self.add_error("discount_value", "Porcentagem máxima: 100%.")
        start, end = cleaned.get("start_date"), cleaned.get("end_date")
        if start and end and end < start:
            self.add_error("end_date", "A data final precisa ser depois da inicial.")
        if cleaned.get("show_top_banner"):
            if not (cleaned.get("banner_text") or cleaned.get("description")):
                self.add_error("banner_text", "Escreva o texto da faixa.")
            # The site applies the banner promotion to every order automatically (it has no coupon field yet)
            if cleaned.get("discount_type") != Promotion.DiscountType.PERCENTAGE:
                self.add_error("show_top_banner", "A faixa do site só aplica desconto em porcentagem (%).")
            if not cleaned.get("coupon_code"):
                self.add_error("show_top_banner", "Defina um código de cupom: é ele que o site envia junto com o pedido.")
            if cleaned.get("min_order_value"):
                self.add_error("show_top_banner", "A faixa do site vale para qualquer pedido: deixe o pedido mínimo em 0.")
            if cleaned.get("registered_customers_only"):
                self.add_error("show_top_banner", "A faixa do site vale para todos: desmarque \"só para Clube VIP\".")
        return cleaned
