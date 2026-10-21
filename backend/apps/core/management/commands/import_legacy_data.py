import json
from pathlib import Path
from decimal import Decimal
from django.core.management.base import BaseCommand
from apps.tenants.models import Tenant
from apps.catalog.models import Category, Product, ProductSizePrice, PizzaCrust
from apps.delivery.models import DeliveryZone, OperatingHour, StoreSettings

class Command(BaseCommand):
    help = (
        "Import initial data from JSON and JS files into Django database (Idempotent). "
        "By default only creates what is missing, so edits made in the owner's panel are kept; "
        "--sobrescrever replaces prices, fees, hours and availability with the files' values."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--sobrescrever",
            action="store_true",
            help="Sobrescreve com os valores dos arquivos o que já existe no banco (desfaz edições do painel).",
        )

    def _sync(self, model, defaults=None, **lookup):
        if self.overwrite:
            return model.objects.update_or_create(defaults=defaults, **lookup)
        return model.objects.get_or_create(defaults=defaults, **lookup)

    def handle(self, *args, **options):
        self.overwrite = options.get("sobrescrever", False)
        self.stdout.write(self.style.NOTICE("Iniciando importacao dos dados legados do Don Corleone..."))
        if not self.overwrite:
            self.stdout.write("Modo seguro: apenas cria o que falta (use --sobrescrever para substituir).")

        from django.conf import settings
        base_dir = settings.BASE_DIR.parent
        src_data_dir = base_dir / "src" / "data"



        # 1. Tenant Don Corleone
        tenant, created = self._sync(Tenant, 
            slug="don-corleone",
            defaults={
                "name": "Don Corleone — Cantina & Pizzaria",
                "segment": "Pizzaria e Esfiharia — Delivery e Retirada",
                "phone": "(65) 99265-0139",
                "whatsapp_number": "5565992650139",
                "address": "Avenida Brasil, 2055, Cidade Alta",
                "city": "Cuiabá",
                "state": "MT",
                "is_active": True
            }
        )
        self.stdout.write(self.style.SUCCESS(f"[OK] Tenant garantido: {tenant.name}"))

        # 2. Store Settings
        settings_obj, _ = self._sync(StoreSettings, 
            tenant=tenant,
            defaults={
                "minimum_order": Decimal("23.00"),
                "pix_key": "65993605364",
                "pix_type": "Celular / WhatsApp",
                "pix_holder": "Don Corleone Pizzaria & Esfiharia",
                "delivery_time_text": "40 a 60 min",
                "pickup_time_text": "20 a 35 min"
            }
        )
        self.stdout.write(self.style.SUCCESS("[OK] Configurações da loja garantidas"))

        # 3. Operating Hours
        hours_data = [
            {"weekday": 0, "name": "Domingo", "abertura": "17:30", "fechamento": "23:15", "corte": "23:00"},
            {"weekday": 1, "name": "Segunda-feira", "abertura": "17:30", "fechamento": "23:00", "corte": "22:45"},
            {"weekday": 2, "name": "Terça-feira", "abertura": "17:30", "fechamento": "23:00", "corte": "22:45"},
            {"weekday": 3, "name": "Quarta-feira", "abertura": "17:30", "fechamento": "23:00", "corte": "22:45"},
            {"weekday": 4, "name": "Quinta-feira", "abertura": "17:30", "fechamento": "23:00", "corte": "22:45"},
            {"weekday": 5, "name": "Sexta-feira", "abertura": "17:30", "fechamento": "23:15", "corte": "23:00"},
            {"weekday": 6, "name": "Sábado", "abertura": "17:30", "fechamento": "23:30", "corte": "23:15"}
        ]
        for h in hours_data:
            self._sync(OperatingHour, 
                tenant=tenant,
                weekday=h["weekday"],
                defaults={
                    "name": h["name"],
                    "opening_time": h["abertura"],
                    "closing_time": h["fechamento"],
                    "cutoff_time": h["corte"],
                    "is_active": True
                }
            )
        self.stdout.write(self.style.SUCCESS("[OK] Horários de funcionamento semanais garantidos"))

        # 4. Pizza Crusts (Bordas Recheadas)
        crusts_data = [
            {"slug": "sem-borda", "name": "Massa Tradicional (Sem Borda)", "price": Decimal("0.00"), "price_text": "Sem adicional", "is_default": True, "is_highlight": False, "order": 1},
            {"slug": "borda-catupiry", "name": "Borda de Catupiry", "price": Decimal("0.00"), "price_text": "Grátis", "is_default": False, "is_highlight": True, "order": 2},
            {"slug": "borda-cheddar", "name": "Borda de Cheddar", "price": Decimal("9.90"), "price_text": "+ R$ 9,90", "is_default": False, "is_highlight": False, "order": 3},
            {"slug": "borda-mussarela", "name": "Borda de Mussarela", "price": Decimal("9.90"), "price_text": "+ R$ 9,90", "is_default": False, "is_highlight": False, "order": 4},
            {"slug": "borda-requeijao", "name": "Borda de Requeijão", "price": Decimal("9.90"), "price_text": "+ R$ 9,90", "is_default": False, "is_highlight": False, "order": 5},
            {"slug": "borda-goiabada", "name": "Borda Doce de Goiabada", "price": Decimal("9.90"), "price_text": "+ R$ 9,90", "is_default": False, "is_highlight": False, "order": 6},
            {"slug": "borda-brigadeiro", "name": "Borda Doce de Brigadeiro", "price": Decimal("9.90"), "price_text": "+ R$ 9,90", "is_default": False, "is_highlight": False, "order": 7},
        ]
        for c in crusts_data:
            self._sync(PizzaCrust, 
                tenant=tenant,
                slug=c["slug"],
                defaults={
                    "name": c["name"],
                    "price": c["price"],
                    "price_text": c["price_text"],
                    "is_default": c["is_default"],
                    "is_highlight": c["is_highlight"],
                    "display_order": c["order"],
                    "is_active": True
                }
            )
        self.stdout.write(self.style.SUCCESS(f"[OK] {len(crusts_data)} bordas de pizza garantidas"))

        # 5. Delivery Zones (bairros.json)
        bairros_file = src_data_dir / "bairros.json"
        if bairros_file.exists():
            with open(bairros_file, "r", encoding="utf-8") as f:
                bairros = json.load(f)
            for b in bairros:
                self._sync(DeliveryZone, 
                    tenant=tenant,
                    city=b.get("cidade", "Cuiabá"),
                    neighborhood=b.get("bairro"),
                    defaults={
                        "fee": Decimal(str(b.get("taxa", 8.00))),
                        "is_active": True
                    }
                )
            self.stdout.write(self.style.SUCCESS(f"[OK] {len(bairros)} bairros importados de bairros.json"))

        # 6. Catalog (cardapio.json)
        cardapio_file = src_data_dir / "cardapio.json"
        if cardapio_file.exists():
            with open(cardapio_file, "r", encoding="utf-8") as f:
                cardapio = json.load(f)

            cat_order = 1
            total_prods = 0
            for cat_data in cardapio.get("categorias", []):
                category, _ = self._sync(Category, 
                    tenant=tenant,
                    slug=cat_data["id"],
                    defaults={
                        "name": cat_data["nome"],
                        "description": cat_data.get("descricao", ""),
                        "display_order": cat_order,
                        "is_active": True
                    }
                )
                cat_order += 1

                prod_order = 1
                for item in cat_data.get("itens", []):
                    item_id = item.get("id")
                    nome = item.get("nome")
                    preco_raw = item.get("preco")
                    base_price = Decimal(str(preco_raw)) if preco_raw is not None else None

                    is_pizza = cat_data["id"] in ["pizzas-salgadas", "pizzas-doces"]
                    is_kit = cat_data["id"] == "kits-esfihas"
                    is_combo = cat_data["id"] == "combos-pizzas"

                    ptype = Product.ProductType.PIZZA if is_pizza else (
                        Product.ProductType.KIT_ESFIHA if is_kit else (
                            Product.ProductType.COMBO if is_combo else Product.ProductType.SIMPLE
                        )
                    )

                    cat_preco = item.get("categoriaPreco", "tradicional")
                    if cat_preco not in ['tradicional', 'premium', 'doce', 'especial']:
                        cat_preco = 'tradicional'

                    product, _ = self._sync(Product, 
                        tenant=tenant,
                        slug=item_id,
                        defaults={
                            "category": category,
                            "name": nome,
                            "description": item.get("descricao", ""),
                            "product_type": ptype,
                            "price_category": cat_preco,
                            "base_price": base_price,
                            "price_text": item.get("precoTexto", ""),
                            "tag": item.get("tag", ""),
                            "is_highlight": item.get("destaque", False),
                            "photo_url": item.get("foto", ""),
                            "is_available": True,
                            "display_order": prod_order,
                            "extra_details": {
                                "unidades": item.get("unidades"),
                                "distribuicao": item.get("distribuicao"),
                                "volume": item.get("volume"),
                                "composicao": item.get("composicao")
                            }
                        }
                    )
                    prod_order += 1
                    total_prods += 1

                    # Sizes for pizzas
                    if is_pizza:
                        precos_dict = item.get("precos", {})
                        p_peq = precos_dict.get("pequena", 45.90 if cat_preco == 'tradicional' else 61.90)
                        p_med = precos_dict.get("media", 62.90 if cat_preco == 'tradicional' else 72.90)
                        p_gra = precos_dict.get("grande", 76.90 if cat_preco == 'tradicional' else 86.90)

                        self._sync(ProductSizePrice, 
                            product=product,
                            size_id="pequena",
                            defaults={"size_name": "Pizza Pequena (25cm)", "slices": 4, "max_flavors": 2, "price": Decimal(str(p_peq))}
                        )
                        self._sync(ProductSizePrice, 
                            product=product,
                            size_id="media",
                            defaults={"size_name": "Pizza Média (30cm)", "slices": 6, "max_flavors": 2, "price": Decimal(str(p_med))}
                        )
                        self._sync(ProductSizePrice, 
                            product=product,
                            size_id="grande",
                            defaults={"size_name": "Pizza Grande (35cm)", "slices": 8, "max_flavors": 3, "price": Decimal(str(p_gra))}
                        )

            self.stdout.write(self.style.SUCCESS(f"[OK] {total_prods} produtos e categorias importados com sucesso!"))

        # 7. "Compre Junto" cart suggestions (compre-junto.json)
        compre_junto_file = src_data_dir / "compre-junto.json"
        if compre_junto_file.exists():
            with open(compre_junto_file, "r", encoding="utf-8") as f:
                compre_junto = json.load(f)

            # Hidden category: these items are offered only inside the cart
            hidden_category, _ = self._sync(Category, 
                tenant=tenant,
                slug="compre-junto",
                defaults={"name": "Compre Junto (carrinho)", "display_order": 999, "is_active": False}
            )
            for order, item in enumerate(compre_junto, start=1):
                price = Decimal(str(item["preco"]))
                product = Product.objects.filter(tenant=tenant, slug=item["id"]).first()
                if product and product.category_id != hidden_category.id:
                    # Same id already listed in the menu: keep it there and only fill a missing price
                    if product.base_price is None:
                        product.base_price = price
                        product.save(update_fields=["base_price", "updated_at"])
                    continue
                self._sync(Product, 
                    tenant=tenant,
                    slug=item["id"],
                    defaults={
                        "category": hidden_category,
                        "name": item["nome"],
                        "description": item.get("subtitulo", ""),
                        "product_type": Product.ProductType.SIMPLE,
                        "base_price": price,
                        "price_text": f"R$ {price:.2f}".replace(".", ","),
                        "photo_url": item.get("foto", ""),
                        "is_available": True,
                        "display_order": order,
                    }
                )
            self.stdout.write(self.style.SUCCESS(f"[OK] {len(compre_junto)} itens do Compre Junto garantidos"))

        self.stdout.write(self.style.SUCCESS("Importação concluída com sucesso e dados prontos para a API!"))
