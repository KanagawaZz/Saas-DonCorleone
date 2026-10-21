from datetime import timedelta
from decimal import Decimal
from rest_framework import serializers
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from .models import Order, OrderItem, OrderItemFlavor, OrderStatusHistory, generate_order_code
from apps.catalog.models import Product, PizzaCrust
from apps.delivery.models import DeliveryZone, OperatingHour, StoreSettings
from apps.promotions.models import Promotion
from apps.pricing.services import calculate_pizza_price, PricingError
from apps.tenants.models import Tenant

MAX_ITEM_QUANTITY = 50
# Tolerance for a checkout started right before closing time
CLOSING_GRACE = timedelta(minutes=5)
PRICE_ON_REQUEST_NOTE = "Preço sob consulta (confirmar com a atendente)"

class OrderItemFlavorInputSerializer(serializers.Serializer):
    id = serializers.CharField()
    nome = serializers.CharField(required=False, allow_blank=True)

class OrderItemInputSerializer(serializers.Serializer):
    # Prices sent by the browser (precoUnitario) are ignored on purpose: the server prices from the catalog.
    tipo = serializers.ChoiceField(choices=["pizza", "simples"], default="simples")
    idProduto = serializers.CharField(required=False, allow_blank=True)
    nome = serializers.CharField(required=False, allow_blank=True)
    quantidade = serializers.IntegerField(default=1, min_value=1, max_value=MAX_ITEM_QUANTITY)
    observacoes = serializers.CharField(required=False, allow_blank=True, max_length=255)

    # Pizza fields
    tamanho = serializers.DictField(required=False)
    borda = serializers.DictField(required=False, allow_null=True)
    sabores = OrderItemFlavorInputSerializer(many=True, required=False)


def _local_minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(':')
    return int(hours) * 60 + int(minutes)


def check_store_open(tenant: Tenant, now=None):
    """Raises ValidationError when the store does not accept orders right now (same rule as the site)."""
    store = StoreSettings.objects.filter(tenant=tenant).first()
    if store and store.emergency_closed:
        raise serializers.ValidationError(store.emergency_closed_reason or "A loja está fechada no momento.")

    now = timezone.localtime(now)
    # OperatingHour.weekday follows the site convention: 0=Sunday ... 6=Saturday
    weekday = (now.weekday() + 1) % 7
    hours = OperatingHour.objects.filter(tenant=tenant, weekday=weekday).first()
    if not hours:
        return
    if not hours.is_active:
        raise serializers.ValidationError("Não abrimos hoje. Confira nossos horários.")

    current = now.hour * 60 + now.minute
    grace = int(CLOSING_GRACE.total_seconds() // 60)
    if not (_local_minutes(hours.opening_time) <= current < _local_minutes(hours.closing_time) + grace):
        raise serializers.ValidationError(
            f"Estamos fechados agora. Hoje atendemos das {hours.opening_time} às {hours.closing_time}."
        )

class CreateOrderSerializer(serializers.Serializer):
    cliente = serializers.DictField()
    modalidade = serializers.CharField(default="entrega")  # 'entrega' or 'retirada'
    entregaInfo = serializers.DictField(required=False)
    endereco = serializers.DictField(required=False)
    retirada = serializers.DictField(required=False)
    pagamento = serializers.DictField()
    itens = OrderItemInputSerializer(many=True)
    cupom = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    observacoes = serializers.CharField(required=False, allow_blank=True)
    idempotencyKey = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        itens_data = attrs.get('itens', [])
        if not itens_data:
            raise serializers.ValidationError("O carrinho está vazio.")

        cliente_data = attrs.get('cliente', {})
        nome = cliente_data.get('nome', '').strip()
        telefone = cliente_data.get('telefone', '').strip()
        if not nome:
            raise serializers.ValidationError("Informe seu nome.")
        if len(''.join(filter(str.isdigit, telefone))) < 10:
            raise serializers.ValidationError("Informe um telefone/WhatsApp válido.")

        if attrs.get('modalidade') not in Order.FulfillmentMode.values:
            raise serializers.ValidationError("Modalidade inválida. Escolha entrega ou retirada.")
        if (attrs.get('pagamento') or {}).get('forma', 'pix') not in Order.PaymentMethod.values:
            raise serializers.ValidationError("Forma de pagamento inválida.")

        tenant = Tenant.objects.first()
        if not tenant:
            raise serializers.ValidationError("Loja não configurada.")
        attrs['tenant'] = tenant

        check_store_open(tenant)

        items_to_create = []
        subtotal = Decimal('0.00')
        for index, item_data in enumerate(itens_data, start=1):
            try:
                item = self._price_item(tenant, item_data)
            except PricingError as exc:
                raise serializers.ValidationError(f"Item {index}: {exc}")
            subtotal += item['subtotal']
            items_to_create.append(item)
        attrs['items_to_create'] = items_to_create
        attrs['subtotal'] = subtotal

        store = StoreSettings.objects.filter(tenant=tenant).first()
        if store and subtotal < store.minimum_order:
            raise serializers.ValidationError(
                f"O pedido mínimo é de R$ {store.minimum_order:.2f}. Adicione mais itens ao carrinho."
            )

        # Delivery fee: neighborhoods outside the list are accepted and confirmed by the attendant
        attrs['delivery_fee'] = Decimal('0.00')
        attrs['delivery_fee_pending'] = False
        if attrs['modalidade'] == Order.FulfillmentMode.DELIVERY:
            bairro_nome = (attrs.get('endereco') or {}).get('bairro', '').strip()
            zone = DeliveryZone.objects.filter(tenant=tenant, neighborhood__iexact=bairro_nome, is_active=True).first()
            if zone:
                attrs['delivery_fee'] = zone.fee
            else:
                attrs['delivery_fee_pending'] = True

        return attrs

    def _price_item(self, tenant, item_data) -> dict:
        """Prices one cart item exclusively from the catalog."""
        qtd = item_data['quantidade']
        notes = item_data.get('observacoes', '')

        if item_data['tipo'] == 'pizza':
            size_id = ((item_data.get('tamanho') or {}).get('id') or '').lower()
            if not size_id:
                raise PricingError("Escolha o tamanho da pizza.")

            crust = None
            borda_id = (item_data.get('borda') or {}).get('id')
            if borda_id and borda_id != 'sem-borda':
                crust = PizzaCrust.objects.filter(tenant=tenant, slug=borda_id, is_active=True).first()
                if not crust:
                    raise PricingError("A borda escolhida não está disponível.")

            flavor_prods = []
            for sabor in item_data.get('sabores', []):
                prod = Product.objects.filter(
                    tenant=tenant, slug=sabor['id'], product_type=Product.ProductType.PIZZA
                ).first()
                if not prod:
                    raise PricingError(f"Sabor não encontrado no cardápio: {sabor.get('nome') or sabor['id']}.")
                if not prod.is_available:
                    raise PricingError(f"O sabor {prod.name} está esgotado no momento.")
                flavor_prods.append(prod)

            unit_price, size = calculate_pizza_price(flavor_prods, size_id, crust)
            n_flavors = len(flavor_prods)
            return {
                "product_type": "pizza",
                "product_name": f"{size.size_name} ({n_flavors} {'Sabor' if n_flavors == 1 else 'Sabores'})",
                "quantity": qtd,
                "unit_price": unit_price,
                "subtotal": unit_price * qtd,
                "size_id": size.size_id,
                "size_name": size.size_name,
                "crust": crust,
                "crust_name": crust.name if crust else "Sem Borda",
                "crust_price": crust.price if crust else Decimal('0.00'),
                "notes": notes,
                "flavors": [(prod, f"1/{n_flavors}") for prod in flavor_prods],
            }

        prod_id = item_data.get('idProduto')
        prod = Product.objects.filter(tenant=tenant, slug=prod_id).first() if prod_id else None
        if not prod:
            raise PricingError(f"Produto não encontrado no cardápio: {item_data.get('nome') or prod_id or 'sem identificação'}.")
        if not prod.is_available:
            raise PricingError(f"{prod.name} está esgotado no momento.")

        # Items listed as "Sob consulta" have no catalog price: the attendant confirms it on WhatsApp
        unit_price = prod.base_price if prod.base_price is not None else Decimal('0.00')
        if prod.base_price is None:
            notes = f"{PRICE_ON_REQUEST_NOTE}. {notes}" if notes else PRICE_ON_REQUEST_NOTE
        return {
            "product_type": prod.product_type,
            "product": prod,
            "product_name": prod.name,
            "quantity": qtd,
            "unit_price": unit_price,
            "subtotal": unit_price * qtd,
            "notes": notes[:255],
            "flavors": [],
        }

    def _apply_coupon(self, tenant, cupom_code, subtotal) -> tuple[Decimal, str]:
        """
        Validates and consumes a coupon inside the order transaction.
        An invalid coupon does not block the order: it is saved without discount and the reason
        goes to the order notes, so the attendant can explain it to the customer.
        """
        promo = Promotion.objects.select_for_update().filter(
            tenant=tenant, coupon_code__iexact=cupom_code, is_active=True
        ).first()
        if not promo:
            return Decimal('0.00'), f"[CUPOM {cupom_code} NÃO APLICADO: cupom inválido ou inexistente]"

        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        valid, message = promo.is_currently_valid(user=user, order_subtotal=subtotal)
        if not valid:
            return Decimal('0.00'), f"[CUPOM {cupom_code} NÃO APLICADO: {message}]"

        Promotion.objects.filter(pk=promo.pk).update(current_uses=F('current_uses') + 1)
        return promo.calculate_discount(subtotal), ""

    def _customer_user(self):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user
        return None

    def create(self, validated_data):
        tenant = validated_data['tenant']
        cliente_data = validated_data['cliente']
        modalidade = validated_data['modalidade']
        endereco_data = validated_data.get('endereco', {})
        pagamento_data = validated_data['pagamento']
        items_to_create = validated_data['items_to_create']
        subtotal = validated_data['subtotal']
        delivery_fee = validated_data['delivery_fee']
        cupom_code = validated_data.get('cupom', '').strip().upper() if validated_data.get('cupom') else ''
        notes = validated_data.get('observacoes', '')
        if validated_data['delivery_fee_pending']:
            notes = f"[TAXA DE ENTREGA A CONFIRMAR - bairro fora da lista] {notes}".strip()
        idempotency_key = validated_data.get('idempotencyKey')

        # Check idempotency
        if idempotency_key:
            existing = Order.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return existing

        with transaction.atomic():
            discount_amount = Decimal('0.00')
            if cupom_code:
                discount_amount, coupon_warning = self._apply_coupon(tenant, cupom_code, subtotal)
                if coupon_warning:
                    notes = f"{coupon_warning} {notes}".strip()
                    cupom_code = ''

            total_amount = max(Decimal('0.00'), subtotal - discount_amount) + delivery_fee

            # Change calculations for cash
            forma_pag = pagamento_data.get('forma', 'pix')
            precisa_troco = pagamento_data.get('precisaTroco') == 'sim'
            troco_para_raw = pagamento_data.get('trocoPara')
            troco_para_dec = None
            troco_calculado = Decimal('0.00')

            if forma_pag == 'dinheiro' and precisa_troco and troco_para_raw:
                try:
                    num_str = ''.join(c for c in str(troco_para_raw) if c.isdigit() or c in ['.', ','])
                    if ',' in num_str:
                        # Brazilian format: "1.000,50" -> "1000.50"
                        num_str = num_str.replace('.', '').replace(',', '.')
                    troco_para_dec = Decimal(num_str).quantize(Decimal('0.01'))
                    if troco_para_dec > total_amount:
                        troco_calculado = troco_para_dec - total_amount
                except Exception:
                    pass

            # Create Order (retries the random readable code on the rare same-day collision)
            for _ in range(5):
                code = generate_order_code()
                if not Order.objects.filter(readable_code=code).exists():
                    break

            order = Order.objects.create(
                tenant=tenant,
                readable_code=code,
                idempotency_key=idempotency_key,
                customer_user=self._customer_user(),
                customer_name=cliente_data.get('nome', '').strip()[:150],
                customer_phone=''.join(filter(str.isdigit, cliente_data.get('telefone', ''))),
                fulfillment_mode=modalidade,
                # The site sends "logradouro"; "rua" is accepted for other clients
                delivery_street=(endereco_data.get('logradouro') or endereco_data.get('rua') or '')[:255],
                delivery_number=endereco_data.get('numero', '')[:50],
                delivery_complement=endereco_data.get('complemento', '')[:150],
                delivery_neighborhood=endereco_data.get('bairro', '')[:150],
                delivery_city=endereco_data.get('cidade') or 'Cuiabá',
                delivery_reference=endereco_data.get('referencia', '')[:255],
                delivery_zipcode=endereco_data.get('cep', '')[:10],
                pickup_requested_time=(validated_data.get('retirada') or {}).get('horarioPretendido', '')[:50],
                status=Order.Status.NOVO,
                payment_method=forma_pag,
                needs_change=precisa_troco,
                change_for=troco_para_dec,
                calculated_change=troco_calculado,
                subtotal=subtotal,
                discount_amount=discount_amount,
                coupon_applied=cupom_code,
                delivery_fee=delivery_fee,
                total_amount=total_amount,
                notes=notes
            )

            # Create OrderItems
            for item_info in items_to_create:
                order_item = OrderItem.objects.create(
                    order=order,
                    product=item_info.get('product'),
                    product_type_snapshot=item_info['product_type'],
                    product_name_snapshot=item_info['product_name'],
                    quantity=item_info['quantity'],
                    unit_price_snapshot=item_info['unit_price'],
                    subtotal_snapshot=item_info['subtotal'],
                    size_id_snapshot=item_info.get('size_id', ''),
                    size_name_snapshot=item_info.get('size_name', ''),
                    crust=item_info.get('crust'),
                    crust_name_snapshot=item_info.get('crust_name', ''),
                    crust_price_snapshot=item_info.get('crust_price', Decimal('0.00')),
                    notes=item_info.get('notes', '')
                )

                for flavor_prod, proportion in item_info.get('flavors', []):
                    OrderItemFlavor.objects.create(
                        item=order_item,
                        product=flavor_prod,
                        flavor_name_snapshot=flavor_prod.name,
                        proportion=proportion
                    )

            # Create initial status history entry
            OrderStatusHistory.objects.create(
                order=order,
                status=Order.Status.NOVO,
                notes="Pedido enviado pelo site público e registrado no sistema."
            )

            return order

class OrderStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ['status', 'notes', 'created_at']

class OrderItemFlavorSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItemFlavor
        fields = ['id', 'flavor_name_snapshot', 'proportion']

class OrderItemDetailSerializer(serializers.ModelSerializer):
    flavors = OrderItemFlavorSerializer(many=True, read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'product_type_snapshot', 'product_name_snapshot', 'quantity',
            'unit_price_snapshot', 'subtotal_snapshot', 'size_name_snapshot',
            'crust_name_snapshot', 'crust_price_snapshot', 'notes', 'flavors'
        ]

class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemDetailSerializer(many=True, read_only=True)
    status_history = OrderStatusHistorySerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    fulfillment_display = serializers.CharField(source='get_fulfillment_mode_display', read_only=True)
    payment_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'readable_code', 'status', 'status_display', 'customer_name',
            'customer_phone', 'fulfillment_mode', 'fulfillment_display',
            'delivery_street', 'delivery_number', 'delivery_neighborhood',
            'delivery_city', 'delivery_reference', 'delivery_complement', 'delivery_zipcode',
            'pickup_requested_time', 'payment_method', 'payment_display',
            'needs_change', 'change_for', 'calculated_change', 'subtotal',
            'discount_amount', 'coupon_applied', 'delivery_fee', 'total_amount',
            'notes', 'created_at', 'items', 'status_history', 'tracking_url'
        ]
